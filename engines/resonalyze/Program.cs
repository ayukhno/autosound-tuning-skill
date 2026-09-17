// The skill's wrapper around Resonalyze's engines: Auto crossover, then Auto delay, on one layout of
// impulse-response files, the way the Virtual DSP window runs them. The engines are CALLED from the pinned
// submodule (vendor/Resonalyze); what the window does around them is copied into WindowReplica.cs, method by
// method. Built on the Resonalyze fork session's reference call and brief (PAS-008, hub #159), which reproduced
// the window's defaults on the Passat's ir-v7_49 solos byte for byte.
//
//   ResonalyzeEngine <layout.json> <out.json> [--log <file>]
//
// In:  autosound.resonalyze-layout.v1 -- written by skills/autosound-tuning/rew_tool/resonalyze_engine.py.
// Out: autosound.resonalyze-result.v1 -- engine results only, no timings, so two runs compare byte for byte.
// Exit 0 done; 2 the layout cannot be used; 3 an engine refused (the JSON still says what ran and why it stopped).
// Stages, each optional: Auto crossover (or the crossovers the layout gives), Auto delay (committed to the settings),
// repairs (JunctionStage: a tune written back, then Auto delay again), junctions (probes and tunes, read-only).
//
// upstream: DIMOSUS/Resonalyze dsp/CrossoverAutoSetup.cs @ b0ce9fb (MIT) -- called: EstimateBand, Propose, ProposeRanked, ProposeSingle, ReferenceLevelDb, OffsetToReferenceLevel, MeasuredSubElevationDb
// upstream: DIMOSUS/Resonalyze dsp/AutoAlignmentEngine.cs @ b0ce9fb (MIT) -- called: Compute, ComputeStereo
// upstream: DIMOSUS/Resonalyze dsp/GainBalanceEngine.cs @ b0ce9fb (MIT) -- called: Compute
// upstream: DIMOSUS/Resonalyze dsp/ProtectiveHighPassCompensation.cs @ b0ce9fb (MIT) -- called: RemoveFromImpulseResponse, LowestRecoverableFrequencyHz
// upstream: DIMOSUS/Resonalyze dsp/TransferIrDiagnostics.cs @ b0ce9fb (MIT) -- called: DetectCrosstalkHead, CleanCrosstalkHead
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/AlignmentReprocessor.cs @ b0ce9fb (MIT) -- compiled unchanged
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverJunctions.cs @ b0ce9fb (MIT) -- compiled unchanged
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverGroupPlacement.cs @ b0ce9fb (MIT) -- compiled unchanged
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverAlignmentStage.cs @ b0ce9fb (MIT) -- compiled unchanged
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverZone.cs @ b0ce9fb (MIT) -- compiled unchanged
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverAutoSetupOrder.cs @ b0ce9fb (MIT) -- compiled unchanged
// upstream: DIMOSUS/Resonalyze source/Measurements/ImpulseMeasurementView.cs @ b0ce9fb (MIT) -- compiled unchanged
// upstream: DIMOSUS/Resonalyze source/Measurements/MeasuredBand.cs @ b0ce9fb (MIT) -- compiled unchanged
// deviation: the options come from the layout, not from dialogs -- absent fields take the window's defaults (brief §1, §2)
// deviation: a driver type given in the layout replaces the engine's suggestion; the skill always gives one (brief §1.7)
// deviation: the protective high-pass is divided out in memory, as Resonalyze's capture does, not by rewriting the files (brief §4)
//
// Portions copied from Resonalyze, Copyright (c) 2023 dimosus, MIT License (vendor/Resonalyze/License.md).

using System.Diagnostics;
using System.Globalization;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using Resonalyze;
using Resonalyze.Dsp;

CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;

const string LayoutContract = "autosound.resonalyze-layout.v1";
const string ResultContract = "autosound.resonalyze-result.v1";

if (args.Length < 2)
{
    Console.Error.WriteLine("usage: ResonalyzeEngine <layout.json> <out.json> [--log <file>]");
    return 2;
}

string layoutPath = Path.GetFullPath(args[0]);
string outPath = Path.GetFullPath(args[1]);
string? logPath = Array.IndexOf(args, "--log") is int logAt and >= 0 && logAt + 1 < args.Length ? args[logAt + 1] : null;

JsonNode layout;
try
{
    layout = JsonNode.Parse(File.ReadAllText(layoutPath))!;
    if ((string?)layout["contract"] != LayoutContract)
    {
        throw new InvalidDataException($"contract is '{(string?)layout["contract"]}', not '{LayoutContract}'");
    }
}
catch (Exception error) when (error is IOException or JsonException or InvalidDataException or InvalidOperationException)
{
    Console.Error.WriteLine($"{layoutPath}: {error.Message}");
    return 2;
}

string dataDir = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(layoutPath)!, (string)layout["dataDir"]!));
JsonNode processor = layout["processor"]!;
int processorRate = (int)processor["sampleRateHz"]!;
double maxDelayMs = (double)processor["maxDelayMs"]!;
bool distortionFromFile = ((string?)layout["distortion"] ?? "none") == "file";
JsonNode crossoverSpec = layout["autoCrossover"] ?? new JsonObject();
JsonNode delaySpec = layout["autoDelay"] ?? new JsonObject();
bool runCrossover = (bool?)crossoverSpec["run"] ?? true;
bool runDelay = (bool?)delaySpec["run"] ?? true;

var request = new WindowReplica.AutoDelayRequest(
    SceneOffsetMs: (double?)delaySpec["sceneOffsetMs"] ?? 0.25,
    RightHandDrive: (bool?)delaySpec["rightHandDrive"] ?? false,
    AdjustGains: (bool?)delaySpec["adjustGains"] ?? false,
    NearSideCutDb: (double?)delaySpec["nearSideCutDb"] ?? 1.0,
    RearFillOffsetMs: (double?)delaySpec["rearFillOffsetMs"] ?? 15.0);
List<CrossoverFilterFamily> families = crossoverSpec["families"] is JsonArray familyList
    ? familyList.Select(node => Enum.Parse<CrossoverFilterFamily>((string)node!)).ToList()
    : [CrossoverFilterFamily.Butterworth, CrossoverFilterFamily.LinkwitzRiley, CrossoverFilterFamily.Bessel];
double minCrossoverHz = (double?)crossoverSpec["minCrossoverHz"] ?? 20;
double maxCrossoverHz = (double?)crossoverSpec["maxCrossoverHz"] ?? 20_000;
bool independentSlopes = (bool?)crossoverSpec["independentSlopes"] ?? true;

var clock = Stopwatch.StartNew();
var inputs = new JsonArray();
var typeOverrides = new Dictionary<string, DriverType>();
List<Block> blocks;
try
{
    blocks = layout["blocks"]!.AsArray().Select(node =>
    {
        ProtectiveHighPassConfiguration? protective = node!["protective"] is JsonNode spec ? Protective((string)spec!) : null;
        var block = new Block
        {
            Name = (string)node["name"]!,
            Zone = Enum.Parse<VirtualCrossoverZone>((string)node["zone"]!),
            Mono = (bool?)node["mono"] ?? false,
            Left = LoadSide((string)node["left"]!, protective),
            Right = node["right"] is JsonNode right ? LoadSide((string)right!, protective) : null
        };
        if (node["type"] is JsonNode type)
        {
            typeOverrides[block.Name] = Enum.Parse<DriverType>((string)type!);
        }
        if (runCrossover && node["crossover"] != null)
        {
            throw new InvalidDataException($"block '{block.Name}' carries a crossover while Auto crossover is asked to run -- one or the other");
        }
        GivenSettings(block, node);
        return block;
    }).ToList();
}
catch (Exception error) when (error is IOException or JsonException or InvalidDataException or ArgumentException
                                  or InvalidOperationException or NotSupportedException or NullReferenceException)
{
    Console.Error.WriteLine($"{layoutPath}: {error.Message}");
    return 2;
}
Console.Error.WriteLine($"loaded {inputs.Count} files in {clock.ElapsedMilliseconds} ms");

var output = new JsonObject
{
    ["contract"] = ResultContract,
    ["layout"] = Path.GetFileName(layoutPath),
    ["variant"] = new JsonObject
    {
        ["distortionFromFile"] = distortionFromFile,
        ["calibration"] = "none",
        ["processorModel"] = (string?)processor["model"],
        ["processorSampleRateHz"] = processorRate,
        ["maxDelayMs"] = maxDelayMs
    },
    ["inputs"] = inputs,
    ["autoCrossover"] = null,
    ["autoDelay"] = null
};
int exitCode = 0;
List<Block> ordered = blocks;

// ---- Auto crossover
if (runCrossover)
{
    clock.Restart();
    try
    {
        WindowReplica.AutoCrossoverRun crossover = WindowReplica.AutoCrossover(
            blocks, processorRate, families: families, minCrossoverHz: minCrossoverHz,
            maxCrossoverHz: maxCrossoverHz, independentSlopes: independentSlopes, typeOverrides: typeOverrides);
        WindowReplica.ApplyAutoCrossover(crossover);
        // "Reorder the channel blocks" defaults on: blocks take the dialog's order (groups in stage order, low to high).
        List<Block> rowOrder = crossover.Fits
            .OrderBy(fit => VirtualCrossoverAlignmentStages.InOrder.ToList().IndexOf(fit.Plan.Group))
            .SelectMany(fit => fit.Plan.InitIndices)
            .Select(index => crossover.Channels[index].Block)
            .ToList();
        ordered = ReorderIntoSlots(blocks, rowOrder);
        output["autoCrossover"] = CrossoverJson(crossover, ordered);
        Console.Error.WriteLine($"auto crossover in {clock.ElapsedMilliseconds} ms");
    }
    catch (Exception error) when (error is InvalidOperationException or ArgumentException or NotSupportedException)
    {
        output["autoCrossover"] = new JsonObject { ["error"] = error.Message };
        runDelay = false;
        exitCode = 3;
    }
}

output["settingsBeforeDelay"] = new JsonArray(ordered.Select(block => (JsonNode)new JsonObject
{
    ["block"] = block.Name,
    ["left"] = SettingsJson(block.Left.Settings),
    ["right"] = block.Right != null && !block.Mono ? SettingsJson(block.Right.Settings) : null
}).ToArray());

// ---- Auto delay, committed to the settings as the window's Apply does
if (runDelay && !RunDelay("autoDelay", logPath))
{
    exitCode = 3;
}

// ---- The junction stage: repairs first (a tune whose best is written back, then Auto delay again on the repaired
// chains), then the read-only junctions (probes of named variants, constrained searches) on what stands after them.
if (exitCode == 0 && layout["repairs"] is JsonArray repairs && repairs.Count > 0)
{
    var repairJson = new JsonArray();
    bool anyApplied = false;
    foreach (JsonNode? item in repairs)
    {
        repairJson.Add(JunctionStage.Run(item!, ordered, processorRate, applyBest: true, out bool applied));
        anyApplied |= applied;
    }
    output["repairs"] = repairJson;
    if (anyApplied && runDelay && !RunDelay("autoDelayAfterRepairs", logPath == null ? null : logPath + ".after-repairs"))
    {
        exitCode = 3;
    }
}
if (exitCode == 0 && layout["junctions"] is JsonArray junctions && junctions.Count > 0)
{
    output["junctions"] = new JsonArray(junctions
        .Select(item => (JsonNode)JunctionStage.Run(item!, ordered, processorRate, applyBest: false, out _))
        .ToArray());
}

output["settingsFinal"] = new JsonArray(ordered.Select(block => (JsonNode)new JsonObject
{
    ["block"] = block.Name,
    ["left"] = SettingsJson(block.Left.Settings),
    ["right"] = block.Right != null && !block.Mono ? SettingsJson(block.Right.Settings) : null
}).ToArray());

File.WriteAllText(outPath, output.ToJsonString(new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.Error.WriteLine($"wrote {outPath}");
return exitCode;

// ---------------------------------------------------------------- Auto delay

bool RunDelay(string key, string? log)
{
    clock.Restart();
    var delayJson = new JsonObject { ["request"] = RequestJson(request) };
    output[key] = delayJson;
    try
    {
        WindowReplica.AutoDelayRun delay = WindowReplica.AutoDelayStereo(ordered, processorRate, maxDelayMs, request);
        delayJson["bridge"] = new JsonObject
        {
            ["left"] = delay.BridgeLeft,
            ["right"] = delay.BridgeRight,
            ["bandHz"] = new JsonArray(R(delay.BridgeBandLowHz, 2), R(delay.BridgeBandHighHz, 2))
        };
        delayJson["result"] = DelayResultJson(delay, ordered);
        JunctionStage.CommitAutoDelay(delay);
        if (log != null)
        {
            File.WriteAllText(log, delay.Log.ToString());
        }
        Console.Error.WriteLine($"{key} in {clock.ElapsedMilliseconds} ms");
        return true;
    }
    catch (Exception error) when (error is InvalidOperationException or ArgumentException or NotSupportedException)
    {
        delayJson["error"] = error.Message;
        if (error is WindowReplica.DelayRangeException range)
        {
            delayJson["overRange"] = new JsonObject
            {
                ["channel"] = range.Channel,
                ["neededMs"] = R(range.NeededMs, 2),
                ["limitMs"] = range.LimitMs,
                ["rearFillMs"] = range.RearFillMs,
                ["widestCarriesFill"] = range.WidestCarriesFill
            };
        }
        return false;
    }
}

// ---------------------------------------------------------------- inputs

SideState LoadSide(string file, ProtectiveHighPassConfiguration? protective)
{
    string path = Path.Combine(dataDir, file);
    SideState side = IrFile.Load(path, protective);
    if (!distortionFromFile)
    {
        // brief §1.4: for REW-converted files the harmonic positions in REW's buffer are a guess; pass none.
        side = new SideState
        {
            File = side.File,
            TransferImpulseResponse = side.TransferImpulseResponse,
            TransferPeakIndex = side.TransferPeakIndex,
            SampleRate = side.SampleRate,
            TransferCoherence = side.TransferCoherence,
            DistortionCurve = null,
            MeasuredBand = side.MeasuredBand
        };
    }
    inputs.Add(new JsonObject
    {
        ["file"] = file,
        ["md5"] = Convert.ToHexStringLower(MD5.HashData(File.ReadAllBytes(path))),
        ["sampleRate"] = side.SampleRate,
        ["samples"] = side.TransferImpulseResponse.Length,
        ["transferPeakIndex"] = side.TransferPeakIndex,
        ["coherence"] = side.TransferCoherence != null,
        ["distortionCurve"] = side.DistortionCurve != null,
        ["measuredBandHz"] = new JsonArray(R(side.MeasuredBand.LowEdgeHz, 2),
            double.IsFinite(side.MeasuredBand.HighEdgeHz) ? R(side.MeasuredBand.HighEdgeHz, 2) : null),
        ["deEmbedded"] = protective != null ? $"{protective.Kind}:{protective.FrequencyHz.ToString(CultureInfo.InvariantCulture)}:{protective.SlopeDbPerOctave}" : null
    });
    return side;
}

static ProtectiveHighPassConfiguration Protective(string spec)
{
    string[] parts = spec.Split(':');
    if (parts.Length != 3)
    {
        throw new InvalidDataException($"protective '{spec}' is not Kind:Hz:SlopeDbPerOctave");
    }
    return new ProtectiveHighPassConfiguration(
        Enum.Parse<ProtectiveHighPassKind>(parts[0]),
        double.Parse(parts[1], CultureInfo.InvariantCulture),
        int.Parse(parts[2], CultureInfo.InvariantCulture));
}

// A block's settings given by the layout: the crossover when Auto crossover does not run, and the PEQ bank the
// Auto delay honours in the chain (brief §2: gain, crossover, PEQ and phase rotation are read; delay and polarity not).
static void GivenSettings(Block block, JsonNode node)
{
    foreach ((string key, SideState? side) in new[] { ("left", (SideState?)block.Left), ("right", block.Mono ? null : block.Right) })
    {
        if (side == null)
        {
            continue;
        }
        VirtualCrossoverChannelSettings settings = side.Settings;
        if (node["crossover"] is JsonNode crossover)
        {
            settings.CrossoverKind = Enum.Parse<CrossoverKind>((string)crossover["kind"]!);
            if (EdgeOf(crossover["highPass"]) is { } highPass)
            {
                settings.HighPassEdge = highPass;
            }
            if (EdgeOf(crossover["lowPass"]) is { } lowPass)
            {
                settings.LowPassEdge = lowPass;
            }
        }
        if (node["gainDb"] is JsonNode gain)
        {
            settings.GainDb = (double)gain!;
        }
        if (node["phaseRotationDegrees"] is JsonNode rotation)
        {
            settings.PhaseRotationDegrees = (double)rotation!;
        }
        if (node["peq"]?[key] is JsonArray bands)
        {
            settings.PeqBands = bands.Select(band => new PeqBand(
                (double)band!["frequencyHz"]!,
                (double)band["q"]!,
                (double?)band["gainDb"] ?? 0.0,
                Enum.Parse<PeqBandType>((string)band["type"]!))).ToList();
        }
    }
}

static CrossoverEdge? EdgeOf(JsonNode? node) => node == null
    ? null
    : new CrossoverEdge(
        Enum.Parse<CrossoverFilterFamily>((string)node["family"]!),
        (double)node["frequencyHz"]!,
        (int)node["slopeDbPerOctave"]!);

// ---------------------------------------------------------------- outputs

JsonObject CrossoverJson(WindowReplica.AutoCrossoverRun crossover, List<Block> reordered)
{
    WindowReplica.GroupFit primary = crossover.Fits.First(fit => fit.Plan.IsPrimary);
    List<string> primaryNames = primary.Plan.InitIndices.Select(i => crossover.Channels[i].Block.Name).ToList();
    return new JsonObject
    {
        ["options"] = new JsonObject
        {
            ["families"] = new JsonArray(families.Select(family => (JsonNode)family.ToString()).ToArray()),
            ["minCrossoverHz"] = minCrossoverHz,
            ["maxCrossoverHz"] = maxCrossoverHz,
            ["independentSlopes"] = independentSlopes,
            ["subElevationDb"] = crossover.SubElevationDb,
            ["candidateCount"] = 50
        },
        ["channels"] = new JsonArray(crossover.Channels.Select(channel => (JsonNode)new JsonObject
        {
            ["block"] = channel.Block.Name,
            ["zone"] = channel.Block.Zone.ToString(),
            ["group"] = channel.Group.ToString(),
            ["file"] = channel.Block.Left.File,
            ["suggestedType"] = channel.Band.SuggestedType.ToString(),
            ["typeUsed"] = (typeOverrides.TryGetValue(channel.Block.Name, out DriverType used) ? used : channel.Band.SuggestedType).ToString(),
            ["typeSource"] = typeOverrides.ContainsKey(channel.Block.Name) ? "layout" : "suggestion",
            ["bandHz"] = new JsonArray(R(channel.Band.LowHz, 2), R(channel.Band.HighHz, 2)),
            ["bandLevelDb"] = R(channel.Band.LevelDb, 3),
            ["distortionStatus"] = channel.Band.DistortionStatus.ToString(),
            ["distortionBandHz"] = new JsonArray(Finite(channel.Band.DistortionLowHz, 2), Finite(channel.Band.DistortionHighHz, 2))
        }).ToArray()),
        ["groups"] = new JsonArray(crossover.Fits.Select(fit => (JsonNode)new JsonObject
        {
            ["group"] = fit.Plan.Group.ToString(),
            ["primary"] = fit.Plan.IsPrimary,
            ["chainOrder"] = new JsonArray(fit.Plan.InitIndices.Select(i => (JsonNode)crossover.Channels[i].Block.Name).ToArray()),
            ["call"] = fit.Plan.Sources.Count == 1 ? "ProposeSingle" : fit.Plan.ImpulseResponses != null ? "ProposeRanked[0]" : "Propose"
        }).ToArray()),
        ["result"] = new JsonArray(crossover.Channels.Select((channel, i) => (JsonNode)Proposal(channel.Block.Name, crossover.Result[i])).ToArray()),
        ["primaryRankedTop5"] = crossover.PrimaryRanked == null ? null : new JsonArray(crossover.PrimaryRanked.Take(5).Select(ranked =>
            (JsonNode)new JsonObject
            {
                ["totalScore"] = R(ranked.TotalScore, 4),
                ["magnitudeScore"] = R(ranked.MagnitudeScore, 4),
                ["achievabilityPenaltyDb"] = ranked.AchievabilityPenaltyDb is { } penalty ? R(penalty, 4) : null,
                ["isConventional24"] = ranked.IsConventional24,
                ["proposals"] = new JsonArray(ranked.Proposals.Select((proposal, k) => (JsonNode)Proposal(primaryNames[k], proposal)).ToArray())
            }).ToArray()),
        ["blockOrderAfterReorder"] = new JsonArray(reordered.Select(block => (JsonNode)block.Name).ToArray())
    };
}

static JsonObject RequestJson(WindowReplica.AutoDelayRequest request) => new()
{
    ["sceneOffsetMs"] = request.SceneOffsetMs,
    ["rightHandDrive"] = request.RightHandDrive,
    ["adjustGains"] = request.AdjustGains,
    ["nearSideCutDb"] = request.NearSideCutDb,
    ["levelDifferenceDb"] = request.LevelDifferenceDb,
    ["rearFillOffsetMs"] = request.RearFillOffsetMs
};

// CommitAutoDelayResult: delay rounded to 0.01 ms, polarity, gain only where adjusted.
static JsonArray DelayResultJson(WindowReplica.AutoDelayRun delay, List<Block> reordered) =>
    new(delay.Union
        .OrderBy(side => reordered.IndexOf(side.Runtime))
        .ThenBy(side => side.RightSide)
        .Select(side =>
        {
            AlignmentOverride over = delay.Alignment.GetValueOrDefault(side);
            AlignmentDecision? decision = delay.Decisions.GetValueOrDefault(side);
            GainBalanceResult? gain = delay.Gains?.FirstOrDefault(result => result.Channel == side);
            return (JsonNode)new JsonObject
            {
                ["channel"] = side.Name,
                ["file"] = side.State.File,
                ["delayMs"] = Math.Round(over.DelayMs, 2),
                ["invertPolarity"] = over.InvertPolarity,
                ["gainDb"] = gain is { Adjusted: true } ? gain.ProposedGainDb : side.Settings.GainDb,
                ["gainAdjusted"] = gain?.Adjusted ?? false,
                ["decision"] = decision == null ? null : new JsonObject
                {
                    ["kind"] = decision.Kind.ToString(),
                    ["confidence"] = decision.Confidence?.ToString(),
                    ["detail"] = decision.Detail
                },
                ["gainBalance"] = gain == null ? null : new JsonObject
                {
                    ["adjusted"] = gain.Adjusted,
                    ["skipReason"] = gain.SkipReason?.ToString(),
                    ["levelDb"] = R(gain.LevelDb, 3),
                    ["proposedGainDb"] = gain.ProposedGainDb,
                    ["confidence"] = gain.Confidence?.ToString(),
                    ["detail"] = gain.Detail
                }
            };
        }).ToArray());

static JsonObject SettingsJson(VirtualCrossoverChannelSettings settings) => new()
{
    ["crossover"] = settings.CrossoverKind.ToString(),
    ["highPass"] = settings.CrossoverKind is CrossoverKind.HighPass or CrossoverKind.BandPass ? Edge(settings.HighPassEdge) : null,
    ["lowPass"] = settings.CrossoverKind is CrossoverKind.LowPass or CrossoverKind.BandPass ? Edge(settings.LowPassEdge) : null,
    ["gainDb"] = settings.GainDb,
    ["delayMs"] = settings.DelayMs,
    ["invertPolarity"] = settings.InvertPolarity,
    ["phaseRotationDegrees"] = settings.PhaseRotationDegrees,
    ["peqBands"] = settings.PeqBands.Count
};

static JsonObject Proposal(string block, CrossoverProposal proposal) => new()
{
    ["block"] = block,
    ["kind"] = proposal.Kind.ToString(),
    ["highPass"] = Edge(proposal.HighPassEdge),
    ["lowPass"] = Edge(proposal.LowPassEdge),
    ["gainDb"] = proposal.GainDb
};

static JsonObject? Edge(CrossoverEdge? edge) => edge is { } e
    ? new JsonObject { ["family"] = e.Family.ToString(), ["frequencyHz"] = e.FrequencyHz, ["slopeDbPerOctave"] = e.SlopeDbPerOctave }
    : null;

static double R(double value, int digits) => Math.Round(value, digits);

static double? Finite(double value, int digits) => double.IsFinite(value) ? Math.Round(value, digits) : null;

// VirtualCrossoverPanel.ReorderIntoSlots.
static List<T> ReorderIntoSlots<T>(IReadOnlyList<T> all, IReadOnlyList<T> reordered) where T : class
{
    var slots = new HashSet<T>(reordered);
    var result = new List<T>(all.Count);
    int next = 0;
    foreach (T item in all)
    {
        result.Add(slots.Contains(item) ? reordered[next++] : item);
    }
    return result;
}
