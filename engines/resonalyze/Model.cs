// The panel's block, side and file model, as much of it as Auto crossover and Auto delay read.
//
// upstream: DIMOSUS/Resonalyze source/Measurements/ImpulseResponseFile.cs @ b0ce9fb (MIT) -- the fields Virtual DSP reads, versions 4..8
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverSource.cs @ b0ce9fb (MIT) -- ResolvedVirtualDspSource.FromSnapshot, ComputeDistortionCurve
// upstream: DIMOSUS/Resonalyze source/Measurements/ExpSweepMeasurement.cs @ b0ce9fb (MIT) -- the protective high-pass division at capture, applied here on load
// deviation: a file whose achieved sweep band is not stored is refused, not re-derived (ExponentialSineSweep.ComputeSpec is not ported)
//
// Portions copied from Resonalyze, Copyright (c) 2023 dimosus, MIT License (vendor/Resonalyze/License.md).

using System.Numerics;
using System.Text.Json;
using Resonalyze.Dsp;

namespace Resonalyze;

/// <summary>One block of the Virtual DSP panel (VirtualCrossoverChannel + its pair): a driver position with a left and, unless mono, a right side.</summary>
internal sealed class Block
{
    public required string Name { get; init; }
    public required VirtualCrossoverZone Zone { get; init; }
    public required bool Mono { get; init; }
    public bool Enabled { get; init; } = true;
    public bool Bypass { get; init; }
    public required SideState Left { get; init; }
    public SideState? Right { get; init; }

    public SideState? SideState(bool right) => right && !Mono ? Right : Left;
}

/// <summary>What VirtualCrossoverChannelState holds for one side after ResolvedVirtualDspSource.ApplyTo, plus the side's settings.</summary>
internal sealed class SideState
{
    public required string File { get; init; }
    public required Complex[] TransferImpulseResponse { get; init; }
    public required int TransferPeakIndex { get; init; }
    public required int SampleRate { get; init; }
    public double[]? TransferCoherence { get; init; }
    public IReadOnlyList<SignalPoint>? DistortionCurve { get; init; }
    public MeasuredBand MeasuredBand { get; init; } = MeasuredBand.Everything;
    public VirtualCrossoverChannelSettings Settings { get; } = new();
}

/// <summary>As VirtualCrossoverSideAlignmentChannel: a mono block contributes ONE instance to both sides; identity is by reference.</summary>
internal sealed class SideChannel : IAlignmentChannel
{
    private readonly int processorSampleRate;

    public SideChannel(Block runtime, bool rightSide, int processorSampleRate)
    {
        Runtime = runtime;
        RightSide = rightSide;
        this.processorSampleRate = processorSampleRate;
    }

    public Block Runtime { get; }
    public bool RightSide { get; }
    public SideState State => Runtime.SideState(RightSide)!;
    public VirtualCrossoverChannelSettings Settings => State.Settings;
    public string Name => Runtime.Mono
        ? $"{Runtime.Name} (mono)"
        : $"{Runtime.Name} {(RightSide ? "R" : "L")}";
    public int SampleRate => State.SampleRate;
    public int ProcessorSampleRate => processorSampleRate > 0 ? processorSampleRate : State.SampleRate;
}

/// <summary>Reads a resonalyze-impulse-response file (v4..v8) the way ImpulseResponseFile + MeasurementHistoryService.CreateSnapshot +
/// ResolvedVirtualDspSource.FromSnapshot do, for the fields Virtual DSP uses.</summary>
internal static class IrFile
{
    public static SideState Load(string path, ProtectiveHighPassConfiguration? deEmbed = null)
    {
        using FileStream stream = File.OpenRead(path);
        using JsonDocument document = JsonDocument.Parse(stream, new JsonDocumentOptions
        {
            AllowTrailingCommas = true,
            CommentHandling = JsonCommentHandling.Skip
        });
        JsonElement root = document.RootElement;
        if (Str(root, "format") != "resonalyze-impulse-response")
        {
            throw new InvalidDataException($"{path}: not a Resonalyze impulse-response file.");
        }
        int version = root.GetProperty("version").GetInt32();
        if (version is < 4 or > 8)
        {
            throw new InvalidDataException($"{path}: format version {version} is outside 4..8.");
        }
        if (Str(root, "timingReference") == "RecordedSweep")
        {
            throw new InvalidDataException($"{path}: a RecordedSweep file has no loopback time base (refused by Virtual DSP).");
        }

        int sampleRate = root.GetProperty("sampleRate").GetInt32();
        double[] transferReal = Samples(root, "transferRealSamples")
            ?? throw new InvalidDataException($"{path}: no transferRealSamples.");
        double[]? transferImag = Samples(root, "transferImaginarySamples");
        Complex[] transfer = ToComplex(transferReal, transferImag);
        int peak = Math.Clamp(Int(root, "transferPeakIndex") ?? 0, 0, transfer.Length - 1);
        double[]? coherence = Samples(root, "transferCoherence");

        double achievedLow = Num(root, "achievedLowFrequencyHz");
        double achievedHigh = Num(root, "achievedHighFrequencyHz");
        if (!(achievedLow > 0 && achievedHigh > achievedLow))
        {
            // ImpulseResponseFile.ResolveAchievedSweepBand re-derives it through ExponentialSineSweep.ComputeSpec (source/, not ported).
            throw new NotSupportedException($"{path}: no achieved sweep band stored.");
        }
        double measuredLow = Num(root, "measuredLowFrequencyHz") > 0
            ? Num(root, "measuredLowFrequencyHz")
            : achievedLow;
        double measuredHigh = Num(root, "measuredHighFrequencyHz") > measuredLow
            ? Num(root, "measuredHighFrequencyHz")
            : achievedHigh;
        ProtectiveHighPassConfiguration? protective = Protective(root);

        if (deEmbed is { Enabled: true })
        {
            if (protective is { Enabled: true })
            {
                throw new InvalidDataException($"{path}: already carries a compensated protective high-pass.");
            }
            // As ExpSweepMeasurement at capture time: divide the filter out, record it, re-find the peak.
            ProtectiveHighPassCompensationResult compensation =
                ProtectiveHighPassCompensation.RemoveFromImpulseResponse(
                    transfer, deEmbed.ToEdge(), sampleRate,
                    ProtectiveHighPassConfiguration.MaximumCompensationBoostDb);
            transfer = compensation.ImpulseResponse;
            coherence = compensation.MaskCoherence(coherence);
            peak = VirtualCrossoverAnalysis.FindPeakIndex(transfer);
            protective = deEmbed;
        }

        return new SideState
        {
            File = Path.GetFileName(path),
            TransferImpulseResponse = transfer,
            TransferPeakIndex = peak,
            SampleRate = sampleRate,
            TransferCoherence = coherence,
            DistortionCurve = Distortion(root, sampleRate, achievedLow, achievedHigh),
            MeasuredBand = MeasuredBand.Resolve(protective, measuredLow, measuredHigh, sampleRate)
        };
    }

    // ResolvedVirtualDspSource.ComputeDistortionCurve.
    private static IReadOnlyList<SignalPoint>? Distortion(
        JsonElement root, int sampleRate, double achievedLow, double achievedHigh)
    {
        double[]? real = Samples(root, "sweepDeconvolutionRealSamples");
        double duration = Num(root, "sweepDurationSeconds");
        if (real is not { Length: > 0 } || sampleRate <= 0 ||
            !double.IsFinite(duration) || duration <= 0)
        {
            return null;
        }

        try
        {
            int sweepSamples = (int)Math.Round(duration * sampleRate);
            var sweep = new EssSweepMetadata(
                achievedLow,
                achievedHigh,
                duration,
                sampleRate,
                sweepSamples,
                Int(root, "sweepDeconvolutionPeakIndex") ?? 0);
            EssHarmonicDecomposition decomposition = EssHarmonicAnalysis.AnalyzeEssHarmonics(
                real, sweep, new HarmonicAnalysisOptions(MaxHarmonic: 5));
            DistortionSpectrum spectrum = EssDistortion.ComputeDistortion(
                decomposition, calibration: null, new DistortionOptions(MaxHarmonic: 5));

            var points = new List<SignalPoint>(spectrum.Frequencies.Length);
            for (int i = 0; i < spectrum.Frequencies.Length; i++)
            {
                double thd = spectrum.ThdRatio[i];
                points.Add(new SignalPoint(
                    spectrum.Frequencies[i],
                    double.IsFinite(thd) && thd > 0.0 ? 20.0 * Math.Log10(thd) : double.NaN));
            }

            return points;
        }
        catch (ArgumentException)
        {
            return null;
        }
    }

    private static ProtectiveHighPassConfiguration? Protective(JsonElement root)
    {
        if (!root.TryGetProperty("protectiveHighPass", out JsonElement element) ||
            element.ValueKind != JsonValueKind.Object)
        {
            return null;
        }

        ProtectiveHighPassKind kind = Enum.Parse<ProtectiveHighPassKind>(
            element.GetProperty("kind").GetString()!, ignoreCase: true);
        return new ProtectiveHighPassConfiguration(
            kind,
            element.GetProperty("frequencyHz").GetDouble(),
            element.GetProperty("slopeDbPerOctave").GetInt32());
    }

    private static Complex[] ToComplex(double[] real, double[]? imaginary)
    {
        var samples = new Complex[real.Length];
        for (int i = 0; i < real.Length; i++)
        {
            samples[i] = new Complex(
                real[i],
                imaginary != null && i < imaginary.Length ? imaginary[i] : 0.0);
        }
        return samples;
    }

    // Float32SampleArrayJsonConverter: number arrays keep double precision; strings are base64 float32 LE.
    private static double[]? Samples(JsonElement root, string name)
    {
        if (!root.TryGetProperty(name, out JsonElement element))
        {
            return null;
        }
        if (element.ValueKind == JsonValueKind.Array)
        {
            var samples = new double[element.GetArrayLength()];
            int i = 0;
            foreach (JsonElement item in element.EnumerateArray())
            {
                samples[i++] = item.GetDouble();
            }
            return samples;
        }
        if (element.ValueKind == JsonValueKind.String)
        {
            byte[] bytes = element.GetBytesFromBase64();
            var samples = new double[bytes.Length / sizeof(float)];
            for (int i = 0; i < samples.Length; i++)
            {
                samples[i] = BitConverter.ToSingle(bytes, i * sizeof(float));
            }
            return samples;
        }
        return null;
    }

    private static string? Str(JsonElement root, string name) =>
        root.TryGetProperty(name, out JsonElement element) && element.ValueKind == JsonValueKind.String
            ? element.GetString()
            : null;

    private static double Num(JsonElement root, string name) =>
        root.TryGetProperty(name, out JsonElement element) && element.ValueKind == JsonValueKind.Number
            ? element.GetDouble()
            : 0.0;

    private static int? Int(JsonElement root, string name) =>
        root.TryGetProperty(name, out JsonElement element) && element.ValueKind == JsonValueKind.Number
            ? element.GetInt32()
            : null;
}
