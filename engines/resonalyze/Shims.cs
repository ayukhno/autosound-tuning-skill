// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverProjectFile.cs @ b0ce9fb (MIT) -- VirtualCrossoverChannelSettings, IIR part only
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverProcessingCoordinator.cs @ b0ce9fb (MIT) -- DspChannelChainCacheKey
// upstream: DIMOSUS/Resonalyze source/Measurements/SweepMeasurementConfiguration.cs @ b0ce9fb (MIT) -- ProtectiveHighPassKind, ProtectiveHighPassConfiguration (the members MeasuredBand reads)
// deviation: no FIR stage in the channel settings -- the IIR spec is always the effective one
//
// Portions copied from Resonalyze, Copyright (c) 2023 dimosus, MIT License (vendor/Resonalyze/License.md).

using Resonalyze.Dsp;

namespace Resonalyze;

// Stand-ins for types whose files drag WinForms, audio or history code into the build.
// Members are copied verbatim from the files named; only the paths Auto crossover and Auto delay read are kept.

/// <summary>From source/Tools/VirtualCrossover/VirtualCrossoverProjectFile.cs (VirtualCrossoverChannelSettings), IIR only: no FIR stage.</summary>
public sealed class VirtualCrossoverChannelSettings
{
    public double GainDb { get; set; }
    public double DelayMs { get; set; }
    public bool InvertPolarity { get; set; }

    public CrossoverKind CrossoverKind { get; set; } = CrossoverKind.Off;
    public CrossoverEdge LowPassEdge { get; set; } =
        new(CrossoverFilterFamily.LinkwitzRiley, 2_000, 24);
    public CrossoverEdge HighPassEdge { get; set; } =
        new(CrossoverFilterFamily.LinkwitzRiley, 2_000, 24);

    public double PhaseRotationDegrees { get; set; }

    public double PeqPreampDb { get; set; }
    public List<PeqBand> PeqBands { get; set; } = new();

    // No FIR here, so the IIR spec is always the effective one.
    public CrossoverSpec EffectiveCrossover =>
        new(CrossoverKind, LowPassEdge, HighPassEdge);

    public double? EffectiveHighPassHz =>
        EffectiveCrossover is { Kind: CrossoverKind.HighPass or CrossoverKind.BandPass, HighPassEdge: { } edge }
            ? edge.FrequencyHz
            : null;

    public double? EffectiveLowPassHz =>
        EffectiveCrossover is { Kind: CrossoverKind.LowPass or CrossoverKind.BandPass, LowPassEdge: { } edge }
            ? edge.FrequencyHz
            : null;

    public DspChannelChain ToChain(VirtualCrossoverZone zone)
    {
        CrossoverSpec crossover = CrossoverKind switch
        {
            CrossoverKind.LowPass => new CrossoverSpec(CrossoverKind, LowPassEdge),
            CrossoverKind.HighPass => new CrossoverSpec(CrossoverKind, HighPassEdge: HighPassEdge),
            CrossoverKind.BandPass => new CrossoverSpec(CrossoverKind, LowPassEdge, HighPassEdge),
            _ => CrossoverSpec.Off
        };
        EqualizationCurve? peq = PeqBands.Count > 0 || PeqPreampDb != 0
            ? new EqualizationCurve(PeqBands, PeqPreampDb)
            : null;
        return new DspChannelChain(
            GainDb,
            DelayMs,
            InvertPolarity,
            crossover,
            peq,
            PhaseRotation(zone),
            Fir: null);
    }

    public PhaseRotationSpec PhaseRotation(VirtualCrossoverZone zone)
    {
        bool referenceIsLowPass = zone == VirtualCrossoverZone.Sub;
        return new PhaseRotationSpec(
            PhaseRotationDegrees,
            (referenceIsLowPass ? LowPassEdge : HighPassEdge).FrequencyHz,
            referenceIsLowPass);
    }
}

/// <summary>From source/Tools/VirtualCrossover/VirtualCrossoverProcessingCoordinator.cs.</summary>
internal sealed class DspChannelChainCacheKey : IEquatable<DspChannelChainCacheKey>
{
    private readonly double gainDb;
    private readonly double delayMs;
    private readonly bool invertPolarity;
    private readonly CrossoverSpec? crossover;
    private readonly double peqPreampDb;
    private readonly PeqBand[] peqBands;
    private readonly PhaseRotationSpec phaseRotation;
    private readonly FirFilter? fir;

    public DspChannelChainCacheKey(DspChannelChain chain)
    {
        ArgumentNullException.ThrowIfNull(chain);
        gainDb = chain.GainDb;
        delayMs = chain.DelayMs;
        invertPolarity = chain.InvertPolarity;
        crossover = chain.Crossover;
        peqPreampDb = chain.Peq?.PreampDb ?? 0;
        peqBands = chain.Peq?.Bands.ToArray() ?? Array.Empty<PeqBand>();
        phaseRotation = chain.PhaseRotation;
        fir = chain.Fir;
    }

    public bool Equals(DspChannelChainCacheKey? other) =>
        other != null &&
        gainDb == other.gainDb &&
        delayMs == other.delayMs &&
        invertPolarity == other.invertPolarity &&
        EqualityComparer<CrossoverSpec?>.Default.Equals(crossover, other.crossover) &&
        peqPreampDb == other.peqPreampDb &&
        phaseRotation == other.phaseRotation &&
        ReferenceEquals(fir, other.fir) &&
        peqBands.SequenceEqual(other.peqBands);

    public override bool Equals(object? obj) =>
        obj is DspChannelChainCacheKey other && Equals(other);

    public override int GetHashCode()
    {
        var hash = new HashCode();
        hash.Add(gainDb);
        hash.Add(delayMs);
        hash.Add(invertPolarity);
        hash.Add(crossover);
        hash.Add(peqPreampDb);
        hash.Add(phaseRotation);
        hash.Add(fir);
        foreach (PeqBand band in peqBands)
        {
            hash.Add(band);
        }
        return hash.ToHashCode();
    }
}

/// <summary>From source/Measurements/SweepMeasurementConfiguration.cs.</summary>
public enum ProtectiveHighPassKind
{
    Off,
    Butterworth,
    LinkwitzRiley
}

/// <summary>From source/Measurements/SweepMeasurementConfiguration.cs, the members MeasuredBand reads.</summary>
public sealed record ProtectiveHighPassConfiguration(
    ProtectiveHighPassKind Kind = ProtectiveHighPassKind.Off,
    double FrequencyHz = 2_000.0,
    int SlopeDbPerOctave = 24)
{
    public const double MaximumCompensationBoostDb = 40.0;

    public bool Enabled => Kind != ProtectiveHighPassKind.Off;

    public static double LowestMeasuredFrequencyHz(
        ProtectiveHighPassConfiguration? measurementFilter,
        int sampleRate) =>
        measurementFilter is { Enabled: true } filter && sampleRate > 0
            ? ProtectiveHighPassCompensation.LowestRecoverableFrequencyHz(
                filter.ToEdge(),
                sampleRate,
                MaximumCompensationBoostDb)
            : 0.0;

    public CrossoverEdge ToEdge()
    {
        if (!Enabled)
        {
            throw new InvalidOperationException(
                "An off protective high-pass has no crossover edge.");
        }

        CrossoverFilterFamily family = Kind switch
        {
            ProtectiveHighPassKind.Butterworth => CrossoverFilterFamily.Butterworth,
            ProtectiveHighPassKind.LinkwitzRiley => CrossoverFilterFamily.LinkwitzRiley,
            _ => throw new InvalidOperationException(
                "An off protective high-pass has no crossover edge.")
        };
        return new CrossoverEdge(family, FrequencyHz, SlopeDbPerOctave);
    }
}
