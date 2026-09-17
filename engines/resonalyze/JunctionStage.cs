// The junction stage: after Auto delay has been committed to the settings, the junction tuner reads one junction at a
// time on the full chains -- Probe for named variants (a wish against the best, each after its own delay), Tune for a
// constrained search (a family, slopes, a corner window). A repair is a Tune whose best is written back to both sides
// of both blocks, as the window's junction tune writes it; the caller runs Auto delay again afterwards.
//
// upstream: DIMOSUS/Resonalyze dsp/CrossoverJunctionTuner.cs @ b0ce9fb (MIT) -- called: Probe, Tune, WithLowPass, WithHighPass
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverPanel.AgentBridge.cs @ b0ce9fb (MIT) -- BuildJunctionTuneSides, RunAgentTuneJunctionAsync (the options' defaults and the write-back)
// upstream: DIMOSUS/Resonalyze source/Integration/AgentBridge/AgentProposalValidator.cs @ b0ce9fb (MIT) -- DefaultJunctionWindow, CurrentFamilies
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverPanel.cs @ b0ce9fb (MIT) -- CommitAutoDelayResult (delay, polarity, an adjusted gain)
// deviation: a probe reads every side that has both blocks measured, not the one side an agent's junction id names -- a crossover is one filter for both sides
// deviation: a repair writes the tuner's best whether or not it beats the current by the keep margin -- the current broke a limit, so it is not a candidate to keep
//
// Portions copied from Resonalyze, Copyright (c) 2023 dimosus, MIT License (vendor/Resonalyze/License.md).

using System.Text.Json.Nodes;
using Resonalyze.Dsp;

namespace Resonalyze;

internal static class JunctionStage
{
    // VirtualCrossoverPanel.CommitAutoDelayResult: what Apply writes after Auto delay.
    public static void CommitAutoDelay(WindowReplica.AutoDelayRun delay)
    {
        foreach (SideChannel side in delay.Union)
        {
            AlignmentOverride over = delay.Alignment.GetValueOrDefault(side);
            side.Settings.DelayMs = Math.Round(over.DelayMs, 2);
            side.Settings.InvertPolarity = over.InvertPolarity;
            if (delay.Gains?.FirstOrDefault(result => result.Channel == side) is { Adjusted: true } gain)
            {
                side.Settings.GainDb = gain.ProposedGainDb;
            }
        }
    }

    // VirtualCrossoverPanel.AgentBridge.BuildJunctionTuneSides, both sides: a mono block routed to both, two monos read once.
    public static (List<JunctionTuneSide> Sides, string? Refusal) Sides(Block lower, Block upper, IReadOnlyList<Block> blocks)
    {
        var sides = new List<JunctionTuneSide>();
        foreach (bool rightSide in new[] { false, true })
        {
            if (rightSide && lower.Mono && upper.Mono)
            {
                continue;
            }
            SideState? lowerState = lower.SideState(rightSide && !lower.Mono);
            SideState? upperState = upper.SideState(rightSide && !upper.Mono);
            if (lowerState == null || upperState == null)
            {
                continue;
            }
            if (lowerState.SampleRate != upperState.SampleRate)
            {
                return ([], $"the two measurements on the {(rightSide ? "right" : "left")} side have different sample rates");
            }
            sides.Add(new JunctionTuneSide(
                rightSide ? "right" : "left",
                lowerState.TransferImpulseResponse,
                lowerState.Settings.ToChain(lower.Zone),
                upperState.TransferImpulseResponse,
                upperState.Settings.ToChain(upper.Zone),
                lowerState.SampleRate));
        }
        return sides.Count == 0 ? ([], "no side has both blocks measured") : (sides, null);
    }

    // AgentProposalValidator.DefaultJunctionWindow: half an octave each way, on the corner lattice.
    public static (double MinHz, double MaxHz) DefaultWindow(double currentHz) =>
        (Math.Max(20, CrossoverAutoSetup.RoundToLattice(currentHz / Math.Sqrt(2))),
         Math.Min(20_000, CrossoverAutoSetup.RoundToLattice(currentHz * Math.Sqrt(2))));

    // AgentProposalValidator.CurrentFamilies.
    public static List<CrossoverFilterFamily> CurrentFamilies(VirtualCrossoverChannelSettings lower, VirtualCrossoverChannelSettings upper)
    {
        var families = new List<CrossoverFilterFamily>();
        if (lower.CrossoverKind is CrossoverKind.LowPass or CrossoverKind.BandPass)
        {
            families.Add(lower.LowPassEdge.Family);
        }
        if (upper.CrossoverKind is CrossoverKind.HighPass or CrossoverKind.BandPass && !families.Contains(upper.HighPassEdge.Family))
        {
            families.Add(upper.HighPassEdge.Family);
        }
        if (families.Count == 0)
        {
            families.Add(CrossoverFilterFamily.LinkwitzRiley);
        }
        return families;
    }

    /// <summary>One junction item of the layout: a probe of named variants, a tune, or both. Returns its JSON; with
    /// <paramref name="applyBest"/> the tune's best is written to the settings and <paramref name="applied"/> says so.</summary>
    public static JsonObject Run(JsonNode item, IReadOnlyList<Block> blocks, int processorRate, bool applyBest, out bool applied)
    {
        applied = false;
        string lowerName = (string)item["lower"]!;
        string upperName = (string)item["upper"]!;
        var json = new JsonObject { ["lower"] = lowerName, ["upper"] = upperName, ["purpose"] = (string?)item["purpose"] };
        Block? lower = blocks.FirstOrDefault(block => block.Name == lowerName);
        Block? upper = blocks.FirstOrDefault(block => block.Name == upperName);
        if (lower == null || upper == null)
        {
            json["error"] = $"no block named '{(lower == null ? lowerName : upperName)}'";
            return json;
        }
        (List<JunctionTuneSide> sides, string? refusal) = Sides(lower, upper, blocks);
        if (refusal != null)
        {
            json["error"] = refusal;
            return json;
        }
        json["sides"] = new JsonArray(sides.Select(side => (JsonNode)side.Name).ToArray());

        try
        {
            if (item["probe"] is JsonArray asked && asked.Count > 0)
            {
                var variants = new List<JunctionProbeVariant>
                {
                    new("as it stands", sides.Select(side => new JunctionProbeChains(side.LowerChain, side.UpperChain)).ToList())
                };
                foreach (JsonNode? variant in asked)
                {
                    CrossoverEdge? lowPass = Edge(variant!["lowPass"]);
                    CrossoverEdge? highPass = Edge(variant["highPass"]);
                    variants.Add(new JunctionProbeVariant(
                        (string?)variant["label"] ?? $"variant {variants.Count}",
                        sides.Select(side => new JunctionProbeChains(
                            lowPass is { } lp ? CrossoverJunctionTuner.WithLowPass(side.LowerChain, lp) : side.LowerChain,
                            highPass is { } hp ? CrossoverJunctionTuner.WithHighPass(side.UpperChain, hp) : side.UpperChain)).ToList()));
                }
                JunctionProbeResult probed = CrossoverJunctionTuner.Probe(sides, processorRate, variants);
                json["probe"] = new JsonObject
                {
                    ["sharedBandHz"] = new JsonArray(R(probed.SharedBandLowHz, 1), R(probed.SharedBandHighHz, 1)),
                    ["entries"] = new JsonArray(probed.Entries.Select(entry => (JsonNode)new JsonObject
                    {
                        ["label"] = entry.Label,
                        ["lowPass"] = EdgeJson(entry.LowerLowPass),
                        ["highPass"] = EdgeJson(entry.UpperHighPass),
                        ["cornerHz"] = R(entry.CornerHz, 1),
                        ["bandHz"] = new JsonArray(R(entry.BandLowHz, 1), R(entry.BandHighHz, 1)),
                        ["sides"] = Readings(entry.Sides),
                        ["sharedBandSides"] = Readings(entry.SharedBandSides),
                        ["afterDelay"] = Alignments(entry.AfterDelay),
                        ["unavailable"] = entry.Unavailable
                    }).ToArray())
                };
            }

            if (item["tune"] is JsonNode tune)
            {
                VirtualCrossoverChannelSettings lowerSettings = lower.Left.Settings;
                VirtualCrossoverChannelSettings upperSettings = upper.Left.Settings;
                double currentHz = VirtualCrossoverJunctions.GetPairCrossoverHz(lowerSettings, upperSettings);
                (double defaultMin, double defaultMax) = DefaultWindow(currentHz);
                List<CrossoverFilterFamily> families = tune["families"] is JsonArray names && names.Count > 0
                    ? names.Select(name => Enum.Parse<CrossoverFilterFamily>((string)name!)).ToList()
                    : CurrentFamilies(lowerSettings, upperSettings);
                List<int>? slopes = tune["slopes"] is JsonArray list && list.Count > 0
                    ? list.Select(slope => (int)slope!).ToList()
                    : null;
                double minHz = (double?)tune["minHz"] ?? defaultMin;
                double maxHz = (double?)tune["maxHz"] ?? defaultMax;
                if (maxHz < minHz * 1.05)
                {
                    maxHz = CrossoverAutoSetup.RoundToLattice(minHz * Math.Sqrt(2));
                }
                var options = new JunctionTuneOptions(
                    families, slopes, minHz, maxHz,
                    (bool?)tune["independentSlopes"] ?? false,
                    processorRate,
                    (double?)tune["keepMarginDb"] ?? CrossoverJunctionTuner.DefaultKeepMarginDb);
                JunctionTuneResult result = CrossoverJunctionTuner.Tune(sides, options);
                var tuneJson = new JsonObject
                {
                    ["windowHz"] = new JsonArray(minHz, maxHz),
                    ["families"] = new JsonArray(families.Select(family => (JsonNode)family.ToString()).ToArray()),
                    ["slopes"] = slopes == null ? null : new JsonArray(slopes.Select(slope => (JsonNode)slope).ToArray()),
                    ["candidatesEvaluated"] = result.CandidatesEvaluated,
                    ["rankingBandHz"] = new JsonArray(R(result.RankingBandLowHz, 1), R(result.RankingBandHighHz, 1)),
                    ["current"] = Candidate(result.Current),
                    ["best"] = Candidate(result.Best),
                    ["changed"] = result.Changed,
                    ["runnersUp"] = new JsonArray(result.RunnersUp.Select(candidate => (JsonNode)Candidate(candidate)).ToArray()),
                    ["currentAfterDelay"] = Alignments(result.CurrentAfterDelay),
                    ["bestAfterDelay"] = Alignments(result.BestAfterDelay),
                    ["applied"] = false
                };
                if (applyBest && result.Best.LowerLowPass is { } bestLow && result.Best.UpperHighPass is { } bestHigh)
                {
                    WriteBack(lower, bestLow, lowerEdge: true);
                    WriteBack(upper, bestHigh, lowerEdge: false);
                    tuneJson["applied"] = true;
                    applied = true;
                }
                json["tune"] = tuneJson;
            }
        }
        catch (Exception error) when (error is ArgumentException or InvalidOperationException)
        {
            json["error"] = error.Message;
        }
        return json;
    }

    // RunAgentTuneJunctionAsync's write-back: the tuner's one crossover on both sides of the block.
    private static void WriteBack(Block block, CrossoverEdge edge, bool lowerEdge)
    {
        foreach (bool rightSide in new[] { false, true })
        {
            if (rightSide && block.Mono || block.SideState(rightSide) is not { } state)
            {
                continue;
            }
            VirtualCrossoverChannelSettings settings = state.Settings;
            if (lowerEdge)
            {
                settings.LowPassEdge = edge;
                settings.CrossoverKind = settings.CrossoverKind is CrossoverKind.HighPass or CrossoverKind.BandPass
                    ? CrossoverKind.BandPass
                    : CrossoverKind.LowPass;
            }
            else
            {
                settings.HighPassEdge = edge;
                settings.CrossoverKind = settings.CrossoverKind is CrossoverKind.LowPass or CrossoverKind.BandPass
                    ? CrossoverKind.BandPass
                    : CrossoverKind.HighPass;
            }
        }
    }

    private static CrossoverEdge? Edge(JsonNode? node) => node == null
        ? null
        : new CrossoverEdge(
            Enum.Parse<CrossoverFilterFamily>((string)node["family"]!),
            (double)node["frequencyHz"]!,
            (int)node["slopeDbPerOctave"]!);

    public static JsonObject? EdgeJson(CrossoverEdge? edge) => edge is { } e
        ? new JsonObject { ["family"] = e.Family.ToString(), ["frequencyHz"] = e.FrequencyHz, ["slopeDbPerOctave"] = e.SlopeDbPerOctave }
        : null;

    private static JsonObject Candidate(JunctionTuneCandidate candidate) => new()
    {
        ["lowPass"] = EdgeJson(candidate.LowerLowPass),
        ["highPass"] = EdgeJson(candidate.UpperHighPass),
        ["bandHz"] = new JsonArray(R(candidate.BandLowHz, 1), R(candidate.BandHighHz, 1)),
        ["scoreDb"] = Finite(candidate.ScoreDb),
        ["rankingScoreDb"] = Finite(candidate.RankingScoreDb),
        ["sides"] = Readings(candidate.Sides),
        ["rankingSides"] = Readings(candidate.RankingSides)
    };

    private static JsonArray Readings(IReadOnlyList<JunctionTuneReading> readings) =>
        new(readings.Select(reading => (JsonNode)new JsonObject
        {
            ["side"] = reading.Side,
            ["lossDb"] = R(reading.LossDb, 3),
            ["dipDb"] = R(reading.DipDb, 3),
            ["rippleDb"] = R(reading.RippleDb, 3),
            ["scoreDb"] = R(reading.ScoreDb, 3)
        }).ToArray());

    private static JsonArray Alignments(IReadOnlyList<JunctionTuneAlignment> alignments) =>
        new(alignments.Select(alignment => (JsonNode)new JsonObject
        {
            ["side"] = alignment.Side,
            ["extraDelayMs"] = R(alignment.ExtraDelayMs, 3),
            ["invertUpper"] = alignment.InvertUpper,
            ["lossDb"] = R(alignment.LossDb, 3),
            ["dipDb"] = R(alignment.DipDb, 3)
        }).ToArray());

    private static double R(double value, int digits) => Math.Round(value, digits);

    private static double? Finite(double value) => double.IsFinite(value) ? Math.Round(value, 3) : null;
}
