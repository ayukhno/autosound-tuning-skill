// What the Virtual DSP window does around the two engines, copied from its WinForms classes at the pinned commit by
// the Resonalyze fork session (PAS-008, hub #159). Each method names its origin; dialogs are replaced by their defaults.
//
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverPanel.cs @ b0ce9fb (MIT) -- OpenAutoSetupWizard (input part), CoherencePerPoint, CollectStereoSides, PickStereoBridge, StereoBridgeBand, CleanCrosstalkHeads, ComputeStereoAlignment, PlaceLaterStagesStereo, SettleWithinGroup, ApplyInnerSettlement, PlacementDecision, NormalizeStagedDelays, ComputeGainBalance, ReorderIntoSlots
// upstream: DIMOSUS/Resonalyze source/Tools/VirtualCrossover/VirtualCrossoverAutoSetupDialog.cs @ b0ce9fb (MIT) -- Init ordering, UpdateSubElevationRange, ApplyClick, Fit
// deviation: dialogs read their default values (non-interactive); the single-side Auto delay path is not copied -- a one-side run is refused
// deviation: NormalizeStagedDelays throws DelayRangeException (an InvalidOperationException) carrying the numbers, and its message has no rear-fill hint -- the caller (resonalyze_engine.py) names the fill that fits
//
// Portions copied from Resonalyze, Copyright (c) 2023 dimosus, MIT License (vendor/Resonalyze/License.md).

using System.Numerics;
using System.Text;
using Resonalyze.Dsp;

namespace Resonalyze;

/// <summary>What the Virtual DSP window does around the two engines, copied from the WinForms classes at the pinned commit.
/// Each method names its origin; dialogs are replaced by their default values (non-interactive).</summary>
internal static class WindowReplica
{
    // ------------------------------------------------------------------ Auto crossover

    internal sealed record WizardChannel(
        Block Block,
        VirtualCrossoverAlignmentStage Group,
        IReadOnlyList<SignalPoint> MagnitudeDb,
        IReadOnlyList<double>? Coherence,
        IReadOnlyList<SignalPoint>? Distortion,
        DriverBandEstimate Band,
        double? HighPassHz,
        double? LowPassHz,
        Complex[] ImpulseResponse);

    internal sealed record GroupPlan(
        VirtualCrossoverAlignmentStage Group,
        IReadOnlyList<int> InitIndices,
        IReadOnlyList<AutoSetupSource> Sources,
        IReadOnlyList<Complex[]>? ImpulseResponses,
        bool IsPrimary);

    internal sealed record GroupFit(GroupPlan Plan, IReadOnlyList<CrossoverProposal> Proposals);

    internal sealed record AutoCrossoverRun(
        IReadOnlyList<WizardChannel> Channels,
        double? SubElevationDb,
        IReadOnlyList<GroupFit> Fits,
        IReadOnlyList<RankedCrossoverProposal>? PrimaryRanked,
        CrossoverProposal[] Result);

    /// <summary>VirtualCrossoverPanel.OpenAutoSetupWizard + VirtualCrossoverAutoSetupDialog (Init, UpdatePreview, ApplyClick, Fit), dialog defaults.</summary>
    public static AutoCrossoverRun AutoCrossover(
        IReadOnlyList<Block> blocks,
        int processorSampleRateHz,
        bool activeSideRight = false,
        IReadOnlyList<CrossoverFilterFamily>? families = null,
        double minCrossoverHz = 20,
        double maxCrossoverHz = 20_000,
        bool independentSlopes = true,
        IReadOnlyDictionary<string, DriverType>? typeOverrides = null)
    {
        List<Block> participating = blocks
            .Where(block => block.Enabled && block.SideState(activeSideRight) != null)
            .ToList();
        if (participating.Count < 2)
        {
            throw new InvalidOperationException("fewer than two enabled channels have a measurement");
        }

        var wizardOptions = new FrequencyResponseOptions { SmoothingInverseOctaves = 3 };
        var channels = new List<WizardChannel>();
        foreach (Block block in participating)
        {
            SideState side = block.SideState(activeSideRight)!;
            AnalysisCurve curve = DataHelper.GetPrimarySpectrum(
                new ImpulseMeasurementView(side.TransferImpulseResponse, side.TransferPeakIndex, side.SampleRate)
                {
                    LowestMeasuredFrequencyHz = side.MeasuredBand.LowEdgeHz,
                    HighestMeasuredFrequencyHz = side.MeasuredBand.HighEdgeHz
                },
                wizardOptions,
                // CalibrationFor(...): the reference run selects no calibration in the panel.
                calibration: null);
            IReadOnlyList<double>? coherence = side.TransferCoherence is { Length: > 1 } linear
                ? CoherencePerPoint(linear, curve.Points, side.SampleRate)
                : null;
            IReadOnlyList<SignalPoint>? distortion = side.DistortionCurve;
            channels.Add(new WizardChannel(
                block,
                VirtualCrossoverAlignmentStages.StageOf(block.Zone),
                curve.Points,
                coherence,
                distortion,
                CrossoverAutoSetup.EstimateBand(curve.Points, coherence, distortion),
                side.Settings.EffectiveHighPassHz,
                side.Settings.EffectiveLowPassHz,
                side.TransferImpulseResponse));
        }

        // Dialog.Init: rows by group, then by effective band centre (stable).
        var rows = new List<int>();
        foreach (VirtualCrossoverAlignmentStage group in VirtualCrossoverAlignmentStages.InOrder)
        {
            rows.AddRange(channels
                .Select((channel, index) => (channel, index))
                .Where(item => item.channel.Group == group)
                .OrderBy(item => VirtualCrossoverAutoSetupOrder.CenterHz(
                    item.channel.Band, item.channel.HighPassHz, item.channel.LowPassHz))
                .Select(item => item.index));
        }

        IReadOnlyList<CrossoverFilterFamily> selected = families ??
        [
            // familyBoxes order: Butterworth, Linkwitz-Riley, Bessel, all checked.
            CrossoverFilterFamily.Butterworth,
            CrossoverFilterFamily.LinkwitzRiley,
            CrossoverFilterFamily.Bessel
        ];
        double sampleRateHz = participating[0].SideState(activeSideRight)!.SampleRate;
        double ceiling = Math.Min(20_000, sampleRateHz * 0.49);
        double maxHz = Math.Min(maxCrossoverHz, Math.Round(ceiling));

        IEnumerable<VirtualCrossoverAlignmentStage> groupsInOrder = VirtualCrossoverAlignmentStages.InOrder
            .Where(group => rows.Any(row => channels[row].Group == group));
        VirtualCrossoverAlignmentStage primary = groupsInOrder
            .DefaultIfEmpty(VirtualCrossoverAlignmentStage.FrontChain).First();
        List<int> MembersOf(VirtualCrossoverAlignmentStage group) =>
            rows.Where(row => channels[row].Group == group).ToList();

        List<GroupPlan> CurrentPlan(bool withImpulseResponses) => groupsInOrder
            .Select(group =>
            {
                List<int> members = MembersOf(group);
                bool ranked = withImpulseResponses && members.Count > 1;
                return new GroupPlan(
                    group,
                    members,
                    members.Select(row => new AutoSetupSource(
                        channels[row].MagnitudeDb,
                        // TypeComboBox starts at the suggested type; the user may pick another.
                        typeOverrides != null && typeOverrides.TryGetValue(channels[row].Block.Name, out DriverType chosen)
                            ? chosen
                            : channels[row].Band.SuggestedType,
                        channels[row].Coherence,
                        channels[row].Distortion)).ToList(),
                    ranked ? members.Select(row => channels[row].ImpulseResponse).ToList() : null,
                    group == primary);
            })
            .ToList();

        double? subElevation = null;
        CrossoverAutoSetupOptions OptionsFor(bool isPrimary) => new(
            selected,
            minCrossoverHz,
            maxHz,
            independentSlopes,
            sampleRateHz,
            processorSampleRateHz,
            isPrimary ? subElevation : null);

        // UpdatePreview → UpdateSubElevationRange: the magnitude-only fit sets the elevation once, capped at the measured one.
        List<GroupFit> quick = Fit(CurrentPlan(withImpulseResponses: false), OptionsFor, sampleRateHz);
        GroupFit? primaryFit = quick.FirstOrDefault(fit => fit.Plan.IsPrimary);
        if (primaryFit != null && primaryFit.Plan.Sources.Count >= 2)
        {
            double measured = CrossoverAutoSetup.MeasuredSubElevationDb(
                primaryFit.Plan.Sources, primaryFit.Proposals, sampleRateHz);
            subElevation = (double)(decimal)Math.Max(0, Math.Round(measured, 1));
        }

        // ApplyClick: rank the groups that have IRs; ProposeRanked(...)[0] is applied silently.
        List<GroupPlan> plan = CurrentPlan(withImpulseResponses: true);
        List<GroupFit> fits = plan.All(group => group.ImpulseResponses == null)
            ? Fit(CurrentPlan(withImpulseResponses: false), OptionsFor, sampleRateHz)
            : Fit(plan, OptionsFor, sampleRateHz);

        GroupPlan primaryPlan = plan.First(group => group.IsPrimary);
        IReadOnlyList<RankedCrossoverProposal>? primaryRanked = primaryPlan.ImpulseResponses != null
            ? CrossoverAutoSetup.ProposeRanked(primaryPlan.Sources, OptionsFor(true), primaryPlan.ImpulseResponses)
            : null;

        var result = new CrossoverProposal[channels.Count];
        foreach (GroupFit fit in fits)
        {
            for (int i = 0; i < fit.Plan.InitIndices.Count; i++)
            {
                result[fit.Plan.InitIndices[i]] = fit.Proposals[i];
            }
        }

        return new AutoCrossoverRun(channels, subElevation, fits, primaryRanked, result);
    }

    // VirtualCrossoverAutoSetupDialog.Fit, verbatim.
    private static List<GroupFit> Fit(
        IReadOnlyList<GroupPlan> plan,
        Func<bool, CrossoverAutoSetupOptions> options,
        double sampleRateHz)
    {
        var fitted = new IReadOnlyList<CrossoverProposal>[plan.Count];
        double? reference = null;
        foreach (int index in Enumerable.Range(0, plan.Count)
                     .OrderByDescending(index => plan[index].IsPrimary))
        {
            GroupPlan group = plan[index];
            CrossoverAutoSetupOptions groupOptions = options(group.IsPrimary);
            IReadOnlyList<CrossoverProposal> proposals = group.Sources.Count == 1
                ? [CrossoverAutoSetup.ProposeSingle(group.Sources[0], groupOptions)]
                : group.ImpulseResponses != null
                    ? CrossoverAutoSetup.ProposeRanked(
                        group.Sources, groupOptions, group.ImpulseResponses)[0].Proposals
                    : CrossoverAutoSetup.Propose(group.Sources, groupOptions);

            if (group.IsPrimary)
            {
                reference = CrossoverAutoSetup.ReferenceLevelDb(
                    group.Sources, proposals, sampleRateHz);
            }
            else if (reference is { } level)
            {
                proposals = CrossoverAutoSetup.OffsetToReferenceLevel(
                    group.Sources, proposals, sampleRateHz, level);
            }

            fitted[index] = proposals;
        }

        return plan.Select((group, index) => new GroupFit(group, fitted[index])).ToList();
    }

    /// <summary>OpenAutoSetupWizard's write-back: both sides (mono: left), edges only where proposed, gain, rotation reset.</summary>
    public static void ApplyAutoCrossover(AutoCrossoverRun run)
    {
        for (int i = 0; i < run.Channels.Count; i++)
        {
            Block block = run.Channels[i].Block;
            CrossoverProposal proposal = run.Result[i];
            foreach (bool rightSide in new[] { false, true })
            {
                if (block.Mono && rightSide || block.SideState(rightSide) == null)
                {
                    continue;
                }

                VirtualCrossoverChannelSettings settings = block.SideState(rightSide)!.Settings;
                settings.CrossoverKind = proposal.Kind;
                if (proposal.HighPassEdge is { } highPass)
                {
                    settings.HighPassEdge = highPass;
                }
                if (proposal.LowPassEdge is { } lowPass)
                {
                    settings.LowPassEdge = lowPass;
                }
                settings.GainDb = proposal.GainDb;
                settings.PhaseRotationDegrees = 0;
            }
        }
    }

    // VirtualCrossoverPanel.CoherencePerPoint, verbatim.
    private static IReadOnlyList<double> CoherencePerPoint(
        double[] coherence,
        IReadOnlyList<SignalPoint> points,
        int sampleRate)
    {
        int fftLength = 2 * (coherence.Length - 1);
        double lowFactor = Math.Pow(2.0, -1.0 / 6.0);
        double highFactor = Math.Pow(2.0, 1.0 / 6.0);
        var values = new double[points.Count];
        for (int i = 0; i < points.Count; i++)
        {
            double frequency = points[i].X;
            int lo = Math.Max(0, (int)Math.Floor(frequency * lowFactor * fftLength / sampleRate));
            int hi = Math.Min(
                coherence.Length - 1,
                (int)Math.Ceiling(frequency * highFactor * fftLength / sampleRate));
            double sum = 0;
            int count = 0;
            for (int bin = lo; bin <= hi; bin++)
            {
                sum += coherence[bin];
                count++;
            }

            values[i] = count > 0 ? sum / count : 1.0;
        }

        return values;
    }

    // ------------------------------------------------------------------ Auto delay (stereo)

    internal sealed record AutoDelayRequest(
        double SceneOffsetMs = 0.25,
        bool RightHandDrive = false,
        bool AdjustGains = false,
        double NearSideCutDb = 1.0,
        double RearFillOffsetMs = 15.0)
    {
        public double LevelDifferenceDb => RightHandDrive ? NearSideCutDb : -NearSideCutDb;
    }

    internal sealed record AutoDelayRun(
        IReadOnlyList<SideChannel> Union,
        Dictionary<IAlignmentChannel, AlignmentOverride> Alignment,
        Dictionary<IAlignmentChannel, AlignmentDecision> Decisions,
        IReadOnlyList<GainBalanceResult>? Gains,
        string BridgeLeft,
        string BridgeRight,
        double BridgeBandLowHz,
        double BridgeBandHighHz,
        StringBuilder Log);

    /// <summary>VirtualCrossoverPanel.PrepareAutoDelay (stereo branch) + RunStereoProposalAsync, non-interactive.</summary>
    public static AutoDelayRun AutoDelayStereo(
        IReadOnlyList<Block> blocks,
        int processorSampleRateHz,
        double processorMaxDelayMs,
        AutoDelayRequest request)
    {
        (List<SideChannel> leftSide, List<SideChannel> rightSide) =
            CollectStereoSides(blocks, processorSampleRateHz);
        SideChannel bridgeRight = PickStereoBridge(leftSide, rightSide) is { } picked &&
            leftSide.Count(InFrontChain) >= 2
            ? picked
            : throw new NotSupportedException("not a stereo run; the single-side path is not part of this reference call");

        List<SideChannel> union = leftSide.Concat(rightSide).Distinct().ToList();
        if (union.Any(item => item.Runtime.Bypass))
        {
            throw new InvalidOperationException("a participating channel is bypassed");
        }
        if (!union.Any(item => item.Settings.EffectiveCrossover.Kind != CrossoverKind.Off))
        {
            throw new InvalidOperationException("no channel has a crossover configured; set the crossovers first");
        }

        SideChannel bridgeLeft = leftSide.First(item => item.Runtime == bridgeRight.Runtime && !item.RightSide);
        if (StereoBridgeBand(bridgeLeft, bridgeRight) is not (double bridgeBandLowHz, double bridgeBandHighHz))
        {
            throw new InvalidOperationException("the stereo bridge has no usable shared band");
        }

        var log = new StringBuilder();
        var engineAlignment = new Dictionary<IAlignmentChannel, AlignmentOverride>();
        var decisions = new Dictionary<IAlignmentChannel, AlignmentDecision>();
        IReadOnlyList<GainBalanceResult>? gains = null;

        List<SideChannel> chainLeft = [.. leftSide.Where(InFrontChain)];
        List<SideChannel> chainRight = [.. rightSide.Where(InFrontChain)];
        List<SideChannel> later = [.. union.Where(side => !InFrontChain(side))];
        AlignmentReprocessor reprocessor = ComputeStereoAlignment(
            chainLeft, chainRight, union, bridgeLeft, bridgeRight,
            bridgeBandLowHz, bridgeBandHighHz, request.SceneOffsetMs,
            request.RightHandDrive, processorSampleRateHz, processorMaxDelayMs,
            engineAlignment, decisions, log);
        if (later.Count > 0)
        {
            IReadOnlyCollection<IAlignmentChannel> fillCarriers = PlaceLaterStagesStereo(
                request.RightHandDrive ? chainRight : chainLeft,
                request.RightHandDrive ? chainLeft : chainRight,
                later,
                reprocessor,
                engineAlignment,
                decisions,
                request.SceneOffsetMs,
                request.RearFillOffsetMs,
                request.RightHandDrive,
                log);
            NormalizeStagedDelays(
                [.. union.Cast<IAlignmentChannel>()], engineAlignment, log,
                processorMaxDelayMs, request.RearFillOffsetMs, fillCarriers);
        }

        if (request.AdjustGains)
        {
            gains = ComputeGainBalance(
                union.Select(side => (
                    (IAlignmentChannel)side,
                    side.Settings,
                    side.Runtime.Mono,
                    side.RightSide,
                    (IAlignmentChannel?)(side.RightSide
                        ? leftSide.FirstOrDefault(left => left.Runtime == side.Runtime && !left.RightSide)
                        : null))),
                reprocessor, engineAlignment, request.LevelDifferenceDb, log);
        }

        return new AutoDelayRun(
            union, engineAlignment, decisions, gains,
            bridgeLeft.Name, bridgeRight.Name, bridgeBandLowHz, bridgeBandHighHz, log);
    }

    // VirtualCrossoverPanel.CollectStereoSides.
    private static (List<SideChannel> Left, List<SideChannel> Right) CollectStereoSides(
        IEnumerable<Block> blocks, int processorSampleRateHz)
    {
        var left = new List<SideChannel>();
        var right = new List<SideChannel>();
        foreach (Block block in blocks)
        {
            if (block.Enabled && block.Left != null)
            {
                var side = new SideChannel(block, false, processorSampleRateHz);
                left.Add(side);
                if (block.Mono)
                {
                    right.Add(side);
                }
            }

            if (!block.Mono && block.Enabled && block.Right != null)
            {
                right.Add(new SideChannel(block, true, processorSampleRateHz));
            }
        }

        return (left, right);
    }

    // VirtualCrossoverPanel.PickStereoBridge / StereoBridgeBand / InFrontChain.
    private static SideChannel? PickStereoBridge(List<SideChannel> leftSide, List<SideChannel> rightSide) =>
        rightSide
            .Where(item => item.RightSide &&
                InFrontChain(item) &&
                leftSide.Any(left => left.Runtime == item.Runtime && !left.RightSide))
            .OrderBy(item => VirtualCrossoverJunctions.BandCenterHz(item.Settings))
            .LastOrDefault();

    private static (double LowHz, double HighHz)? StereoBridgeBand(SideChannel bridgeLeft, SideChannel bridgeRight)
    {
        (double leftLowHz, double leftHighHz) = VirtualCrossoverJunctions.GetChannelBand(bridgeLeft.Settings);
        (double rightLowHz, double rightHighHz) = VirtualCrossoverJunctions.GetChannelBand(bridgeRight.Settings);
        double lowHz = Math.Max(leftLowHz, rightLowHz);
        double highHz = Math.Min(leftHighHz, rightHighHz);
        return highHz < lowHz * VirtualCrossoverAnalysis.MinimumArrivalBandRatio
            ? null
            : (lowHz, highHz);
    }

    private static bool InFrontChain(SideChannel side) =>
        VirtualCrossoverAlignmentStages.StageOf(side.Runtime.Zone) == VirtualCrossoverAlignmentStage.FrontChain;

    // VirtualCrossoverPanel.CleanCrosstalkHeads.
    private static List<AlignmentReprocessInput> CleanCrosstalkHeads(
        List<AlignmentReprocessInput> inputs,
        StringBuilder log) =>
        inputs.Select(input =>
        {
            double[] real = Array.ConvertAll(input.MeasuredImpulseResponse, sample => sample.Real);
            CrosstalkHeadGate? gate = TransferIrDiagnostics.DetectCrosstalkHead(real, input.SampleRate);
            if (gate is not { } convicted)
            {
                return input;
            }

            log.AppendLine(
                $"{input.Channel.Name}: playback-crosstalk click at " +
                $"{convicted.BurstTimeMs:0.00} ms ({convicted.BurstPeakDbReMax:0.0} dB " +
                "re max) removed from the record's head before the search");
            return input with
            {
                MeasuredImpulseResponse = TransferIrDiagnostics.CleanCrosstalkHead(
                    input.MeasuredImpulseResponse, input.SampleRate, convicted)
            };
        }).ToList();

    // VirtualCrossoverPanel.ComputeStereoAlignment.
    private static AlignmentReprocessor ComputeStereoAlignment(
        List<SideChannel> leftSide,
        List<SideChannel> rightSide,
        List<SideChannel> union,
        SideChannel bridgeLeft,
        SideChannel bridgeRight,
        double bridgeBandLowHz,
        double bridgeBandHighHz,
        double sceneOffsetMs,
        bool rightHandDrive,
        int processorSampleRateHz,
        double maxDelayMs,
        Dictionary<IAlignmentChannel, AlignmentOverride> alignment,
        Dictionary<IAlignmentChannel, AlignmentDecision> decisions,
        StringBuilder log)
    {
        var reprocessor = new AlignmentReprocessor(
            CleanCrosstalkHeads(
                union.Select(side => new AlignmentReprocessInput(
                    side,
                    side.State.TransferImpulseResponse,
                    side.State.SampleRate,
                    processorSampleRateHz,
                    side.Settings.ToChain(side.Runtime.Zone))).ToList(),
                log));

        IReadOnlyList<AlignmentSnapshot> initialSnapshots = reprocessor.Reprocess(
            new Dictionary<IAlignmentChannel, AlignmentOverride>());
        Dictionary<SideChannel, AlignmentSnapshot> initial = union
            .Select((side, i) => (side, snapshot: initialSnapshots[i]))
            .ToDictionary(item => item.side, item => item.snapshot);
        List<AlignmentSnapshot> ByBand(List<SideChannel> sides) => sides
            .OrderBy(side => VirtualCrossoverJunctions.BandCenterHz(side.Settings))
            .Select(side => initial[side])
            .ToList();
        List<AlignmentJunction> Pairs(List<AlignmentSnapshot> byBand)
        {
            var pairs = new List<AlignmentJunction>();
            for (int i = 0; i < byBand.Count - 1; i++)
            {
                double pairHz = VirtualCrossoverJunctions.GetPairCrossoverHz(
                    ((SideChannel)byBand[i].Channel).Settings,
                    ((SideChannel)byBand[i + 1].Channel).Settings);
                (double bandLowHz, double bandHighHz) = VirtualCrossoverJunctions.OverlapBand(pairHz);
                pairs.Add(new AlignmentJunction(byBand[i], byBand[i + 1], pairHz, bandLowHz, bandHighHz));
            }

            return pairs;
        }

        var pairLinks = new List<StereoPairLink>();
        foreach (SideChannel right in rightSide.Where(side => side.RightSide))
        {
            SideChannel? left = leftSide.FirstOrDefault(side => side.Runtime == right.Runtime && !side.RightSide);
            if (left == null)
            {
                continue;
            }

            (double leftLow, double leftHigh) = VirtualCrossoverJunctions.GetChannelBand(left.Settings);
            (double rightLow, double rightHigh) = VirtualCrossoverJunctions.GetChannelBand(right.Settings);
            double lowHz = Math.Max(leftLow, rightLow);
            double highHz = Math.Min(leftHigh, rightHigh);
            if (highHz >= lowHz * VirtualCrossoverAnalysis.MinimumArrivalBandRatio)
            {
                pairLinks.Add(rightHandDrive
                    ? new StereoPairLink(right, left, lowHz, highHz)
                    : new StereoPairLink(left, right, lowHz, highHz));
            }
        }

        List<AlignmentSnapshot> referenceByBand = ByBand(rightHandDrive ? rightSide : leftSide);
        List<AlignmentSnapshot> farByBand = ByBand(rightHandDrive ? leftSide : rightSide);
        AutoAlignmentEngine.ComputeStereo(
            new StereoAlignmentPlan(
                referenceByBand,
                Pairs(referenceByBand),
                farByBand,
                Pairs(farByBand),
                leftSide.Where(side => side.Runtime.Mono).Cast<IAlignmentChannel>().ToList(),
                rightHandDrive ? bridgeRight : bridgeLeft,
                rightHandDrive ? bridgeLeft : bridgeRight,
                bridgeBandLowHz,
                bridgeBandHighHz,
                sceneOffsetMs,
                pairLinks),
            reprocessor.Reprocess,
            alignment,
            log,
            decisions,
            maxDelayMs);
        return reprocessor;
    }

    private const double CentreWitnessToleranceMs = 0.35;
    private const double HaasPolarityIrrelevantMs = 5.0;
    private const double StrongPlacementCoefficient = 0.6;

    // VirtualCrossoverPanel.PlaceLaterStagesStereo.
    private static IReadOnlyCollection<IAlignmentChannel> PlaceLaterStagesStereo(
        IReadOnlyList<SideChannel> chainReference,
        IReadOnlyList<SideChannel> chainFar,
        IReadOnlyList<SideChannel> later,
        AlignmentReprocessor reprocessor,
        Dictionary<IAlignmentChannel, AlignmentOverride> alignment,
        Dictionary<IAlignmentChannel, AlignmentDecision> decisions,
        double sceneOffsetMs,
        double rearFillOffsetMs,
        bool rightHandDrive,
        StringBuilder log)
    {
        var fillCarriers = new List<IAlignmentChannel>();
        IReadOnlyList<AlignmentSnapshot> settled = reprocessor.Reprocess(alignment);
        Dictionary<IAlignmentChannel, AlignmentSnapshot> byChannel = settled.ToDictionary(snapshot => snapshot.Channel);
        Complex[] SumOf(IEnumerable<SideChannel> group) =>
            VirtualCrossoverAnalysis.SumImpulseResponses([.. group.Select(side => byChannel[side].ImpulseResponse)]);
        (double LowHz, double HighHz) BandOf(IEnumerable<SideChannel> group)
        {
            double low = double.MaxValue;
            double high = double.MinValue;
            foreach (SideChannel side in group)
            {
                (double sideLow, double sideHigh) = VirtualCrossoverJunctions.GetChannelBand(side.Settings);
                low = Math.Min(low, sideLow);
                high = Math.Max(high, sideHigh);
            }

            return (low, high);
        }

        Complex[] referenceSum = SumOf(chainReference);
        Complex[] farSum = SumOf(chainFar);
        (double referenceLow, double referenceHigh) = BandOf(chainReference);
        (double farLow, double farHigh) = BandOf(chainFar);
        int sampleRate = chainReference[0].SampleRate;

        foreach (IGrouping<bool, SideChannel> sideGroup in later
            .Where(item => VirtualCrossoverAlignmentStages.StageOf(item.Runtime.Zone) == VirtualCrossoverAlignmentStage.Rear)
            .GroupBy(item => item.RightSide))
        {
            List<SideChannel> members = [.. sideGroup];
            bool far = sideGroup.Key != rightHandDrive;
            Dictionary<IAlignmentChannel, AlignmentOverride> inner = SettleWithinGroup(
                [.. members.Cast<IAlignmentChannel>()],
                member => ((SideChannel)member).Settings,
                byChannel,
                reprocessor,
                log);
            if (inner.Count > 0)
            {
                ApplyInnerSettlement(members, inner, alignment);
                settled = reprocessor.Reprocess(alignment);
                byChannel = settled.ToDictionary(snapshot => snapshot.Channel);
            }

            string name = string.Join("+", members.Select(item => item.Name));
            (double sideLow, double sideHigh) = BandOf(members);
            (SideChannel Channel, double LowHz, double HighHz)? pick =
                VirtualCrossoverGroupPlacement.ChooseReference(
                    far ? chainFar : chainReference,
                    item => VirtualCrossoverJunctions.GetChannelBand(item.Settings),
                    sideLow,
                    sideHigh);
            Complex[] against = pick is { } chosen ? byChannel[chosen.Channel].ImpulseResponse : far ? farSum : referenceSum;
            string againstName = pick is { } named ? named.Channel.Name : "this side's front stage";
            double lowHz = pick?.LowHz ?? Math.Max(far ? farLow : referenceLow, sideLow);
            double highHz = pick?.HighHz ?? Math.Min(far ? farHigh : referenceHigh, sideHigh);
            GroupPlacement? placement = VirtualCrossoverGroupPlacement.Place(against, SumOf(members), sampleRate, lowHz, highHz);
            if (placement == null)
            {
                log.AppendLine($"  rear {name}: not placed - no reliable arrival in {lowHz:0}-{highHz:0} Hz against {againstName}. Its current delay stands.");
                foreach (SideChannel member in members)
                {
                    alignment[member] = new AlignmentOverride(member.Settings.DelayMs, member.Settings.InvertPolarity);
                    decisions[member] = new AlignmentDecision(
                        AlignmentDecisionKind.Locked, null,
                        $"not placed: no reliable arrival in {lowHz:0}-{highHz:0} Hz against {againstName}, so the current delay stands");
                }

                continue;
            }

            fillCarriers.AddRange(members);
            double delayMs = placement.CoArrivalDelayMs + rearFillOffsetMs;
            bool invert = rearFillOffsetMs < HaasPolarityIrrelevantMs && placement.Inverted;
            log.AppendLine(
                $"  rear {name}: {delayMs:+0.00;-0.00;0.00} ms (co-arrival {placement.CoArrivalDelayMs:+0.00;-0.00;0.00}" +
                (rearFillOffsetMs != 0 ? $" plus {rearFillOffsetMs:0.##} ms fill" : string.Empty) +
                $"), against {againstName} in {lowHz:0}-{highHz:0} Hz, r {placement.Coefficient:0.00}" +
                (invert ? ", inverted" : string.Empty) +
                (placement.EdgePinned ? ", pinned to the refinement edge (the arrival stands, no polarity claimed)" : string.Empty));
            foreach (SideChannel member in members)
            {
                double innerMs = inner.TryGetValue(member, out AlignmentOverride own) ? own.DelayMs : 0.0;
                bool innerInvert = inner.TryGetValue(member, out AlignmentOverride flip) && flip.InvertPolarity;
                alignment[member] = new AlignmentOverride(innerMs + delayMs, innerInvert ^ invert);
                decisions[member] = PlacementDecision(
                    placement.Coefficient,
                    corroborated: !placement.EdgePinned,
                    $"placed as a rear group against {againstName} in {lowHz:0}-{highHz:0} Hz, r {placement.Coefficient:0.00}" +
                    (rearFillOffsetMs != 0 ? $", held back {rearFillOffsetMs:0.##} ms" : string.Empty));
            }
        }

        List<SideChannel> centreMembers = [.. later.Where(item =>
            VirtualCrossoverAlignmentStages.StageOf(item.Runtime.Zone) == VirtualCrossoverAlignmentStage.Center)];
        if (centreMembers.Count > 0)
        {
            Dictionary<IAlignmentChannel, AlignmentOverride> inner = SettleWithinGroup(
                [.. centreMembers.Cast<IAlignmentChannel>()],
                member => ((SideChannel)member).Settings,
                byChannel,
                reprocessor,
                log);
            if (inner.Count > 0)
            {
                ApplyInnerSettlement(centreMembers, inner, alignment);
                settled = reprocessor.Reprocess(alignment);
                byChannel = settled.ToDictionary(snapshot => snapshot.Channel);
            }

            string centreName = string.Join("+", centreMembers.Select(item => item.Name));
            (double centreLow, double centreHigh) = BandOf(centreMembers);
            CentreReferenceChoice<SideChannel> choice = VirtualCrossoverGroupPlacement.ChooseCentreReferences(
                chainReference,
                chainFar,
                item => VirtualCrossoverJunctions.GetChannelBand(item.Settings),
                (near, far) => near.Runtime == far.Runtime && near != far,
                centreLow,
                centreHigh);
            if (choice.Plan is not { } plan)
            {
                log.AppendLine($"  centre {centreName}: not placed - {choice.Refusal}. Its current delay stands.");
                foreach (SideChannel member in centreMembers)
                {
                    alignment[member] = new AlignmentOverride(member.Settings.DelayMs, member.Settings.InvertPolarity);
                    decisions[member] = new AlignmentDecision(
                        AlignmentDecisionKind.Locked, null,
                        $"not placed: {choice.Refusal}, so there is no midpoint to place the centre between and the current delay stands");
                }

                return fillCarriers;
            }

            double lowHz = plan.LowHz;
            double highHz = plan.HighHz;
            string Describe(IReadOnlyList<SideChannel> side) =>
                (plan.Peers ? string.Empty : "the own content ") + string.Join("+", side.Select(item => item.Name));
            string nearName = Describe(plan.Near);
            string farName = Describe(plan.Far);
            Complex[] nearIr = SumOf(plan.Near);
            Complex[] farIr = SumOf(plan.Far);

            Complex[] centreIr = SumOf(centreMembers);
            GroupPlacement? againstReference = VirtualCrossoverGroupPlacement.Place(nearIr, centreIr, sampleRate, lowHz, highHz);
            GroupPlacement? againstFar = VirtualCrossoverGroupPlacement.Place(farIr, centreIr, sampleRate, lowHz, highHz);
            if (againstReference == null || againstFar == null)
            {
                log.AppendLine(
                    $"  centre {centreName}: not placed - no reliable arrival in {lowHz:0}-{highHz:0} Hz against " +
                    (againstReference == null ? nearName : farName) + ". Its current delay stands.");
                foreach (SideChannel member in centreMembers)
                {
                    alignment[member] = new AlignmentOverride(member.Settings.DelayMs, member.Settings.InvertPolarity);
                    decisions[member] = new AlignmentDecision(
                        AlignmentDecisionKind.Locked, null,
                        $"not placed: no reliable arrival in {lowHz:0}-{highHz:0} Hz against {nearName} and {farName}, so the current delay stands");
                }

                return fillCarriers;
            }

            (double delayMs, bool inverted, CentreCorroboration corroboration) =
                VirtualCrossoverGroupPlacement.Midpoint(againstReference, againstFar, sceneOffsetMs, CentreWitnessToleranceMs);
            log.AppendLine(
                $"  centre {centreName}: {delayMs:+0.00;-0.00;0.00} ms - midway between " +
                $"{againstReference.CoArrivalDelayMs:+0.00;-0.00;0.00} (vs {nearName}, r {againstReference.Coefficient:0.00}) and " +
                $"{againstFar.CoArrivalDelayMs:+0.00;-0.00;0.00} (vs {farName}, r {againstFar.Coefficient:0.00}) in {lowHz:0}-{highHz:0} Hz" +
                (inverted ? ", inverted" : string.Empty) +
                $" - {corroboration.Describe()}" +
                (corroboration.Confident ? string.Empty : " - LOW CONFIDENCE"));
            foreach (SideChannel member in centreMembers)
            {
                double innerMs = inner.TryGetValue(member, out AlignmentOverride own) ? own.DelayMs : 0.0;
                bool innerInvert = inner.TryGetValue(member, out AlignmentOverride flip) && flip.InvertPolarity;
                alignment[member] = new AlignmentOverride(innerMs + delayMs, innerInvert ^ inverted);
                decisions[member] = PlacementDecision(
                    Math.Min(againstReference.Coefficient, againstFar.Coefficient),
                    corroboration.Confident,
                    $"placed midway between {nearName} and {farName} in {lowHz:0}-{highHz:0} Hz - {corroboration.Describe()}");
            }
        }

        return fillCarriers;
    }

    // VirtualCrossoverPanel.SettleWithinGroup.
    private static Dictionary<IAlignmentChannel, AlignmentOverride> SettleWithinGroup(
        IReadOnlyList<IAlignmentChannel> members,
        Func<IAlignmentChannel, VirtualCrossoverChannelSettings> settingsOf,
        IReadOnlyDictionary<IAlignmentChannel, AlignmentSnapshot> snapshots,
        AlignmentReprocessor reprocessor,
        StringBuilder log)
    {
        var inner = new Dictionary<IAlignmentChannel, AlignmentOverride>();
        if (members.Count < 2)
        {
            return inner;
        }

        List<IAlignmentChannel> byBand = [.. members.OrderBy(member => VirtualCrossoverJunctions.BandCenterHz(settingsOf(member)))];
        var junctions = new List<AlignmentJunction>();
        for (int i = 0; i < byBand.Count - 1; i++)
        {
            double pairHz = VirtualCrossoverJunctions.GetPairCrossoverHz(settingsOf(byBand[i]), settingsOf(byBand[i + 1]));
            (double lowHz, double highHz) = VirtualCrossoverJunctions.OverlapBand(pairHz);
            junctions.Add(new AlignmentJunction(snapshots[byBand[i]], snapshots[byBand[i + 1]], pairHz, lowHz, highHz));
        }

        if (junctions.Count == 0)
        {
            return inner;
        }

        log.AppendLine($"  settling {byBand.Count} drivers within the group ({junctions.Count} junction(s)) before placing it:");
        AutoAlignmentEngine.Compute(
            [.. byBand.Select(member => snapshots[member])],
            junctions,
            reprocessor.Reprocess,
            inner,
            log);
        return inner;
    }

    // VirtualCrossoverPanel.ApplyInnerSettlement.
    private static void ApplyInnerSettlement(
        IEnumerable<IAlignmentChannel> members,
        IReadOnlyDictionary<IAlignmentChannel, AlignmentOverride> inner,
        Dictionary<IAlignmentChannel, AlignmentOverride> alignment)
    {
        foreach (IAlignmentChannel member in members)
        {
            alignment[member] = inner.GetValueOrDefault(member);
        }
    }

    // VirtualCrossoverPanel.PlacementDecision.
    private static AlignmentDecision PlacementDecision(double coefficient, bool corroborated, string detail)
    {
        AlignmentConfidence confidence =
            !corroborated || coefficient < VirtualCrossoverGroupPlacement.MinimumTrustedCoefficient
                ? AlignmentConfidence.Low
                : coefficient >= StrongPlacementCoefficient
                    ? AlignmentConfidence.High
                    : AlignmentConfidence.Medium;
        return new AlignmentDecision(AlignmentDecisionKind.Search, confidence, detail);
    }

    // VirtualCrossoverPanel.NormalizeStagedDelays (the over-range message without the rear-fill hint).
    private static void NormalizeStagedDelays(
        IReadOnlyList<IAlignmentChannel> scope,
        Dictionary<IAlignmentChannel, AlignmentOverride> alignment,
        StringBuilder log,
        double maxDelayMs,
        double rearFillOffsetMs,
        IReadOnlyCollection<IAlignmentChannel>? rearFillCarriers)
    {
        if (scope.Count == 0)
        {
            return;
        }

        Dictionary<IAlignmentChannel, double> raw = scope.Distinct().ToDictionary(
            channel => channel,
            channel => alignment.GetValueOrDefault(channel).DelayMs);

        double minimum = raw.Values.Min();
        if (minimum < 0)
        {
            log.AppendLine($"  normalization: every channel shifted +{-minimum:0.00} ms so the earliest sits at zero.");
            foreach (IAlignmentChannel channel in raw.Keys)
            {
                AlignmentOverride over = alignment.GetValueOrDefault(channel);
                alignment[channel] = over with { DelayMs = over.DelayMs - minimum };
            }
        }

        IAlignmentChannel widest = raw.Keys.MaxBy(channel => alignment.GetValueOrDefault(channel).DelayMs)!;
        double widestDelayMs = alignment.GetValueOrDefault(widest).DelayMs;
        if (widestDelayMs <= maxDelayMs + 0.005)
        {
            return;
        }

        throw new DelayRangeException(
            widest.Name,
            widestDelayMs,
            maxDelayMs,
            rearFillOffsetMs,
            rearFillCarriers?.Contains(widest) == true,
            "The staged alignment does not fit the DSP delay range: " +
            $"{widest.Name} needs {widestDelayMs:0.00} ms with the earliest channel at 0, but the limit is {maxDelayMs:0.##} ms " +
            $"(rear fill {rearFillOffsetMs:0.##} ms on {rearFillCarriers?.Count ?? 0} channel(s)).");
    }

    /// <summary>The over-range refusal with its numbers, so the caller can name the rear fill that would fit.</summary>
    internal sealed class DelayRangeException(
        string channel, double neededMs, double limitMs, double rearFillMs, bool widestCarriesFill, string message)
        : InvalidOperationException(message)
    {
        public string Channel { get; } = channel;
        public double NeededMs { get; } = neededMs;
        public double LimitMs { get; } = limitMs;
        public double RearFillMs { get; } = rearFillMs;
        public bool WidestCarriesFill { get; } = widestCarriesFill;
    }

    // VirtualCrossoverPanel.ComputeGainBalance.
    private static IReadOnlyList<GainBalanceResult> ComputeGainBalance(
        IEnumerable<(IAlignmentChannel Channel, VirtualCrossoverChannelSettings Settings,
            bool Mono, bool RightSide, IAlignmentChannel? LeftPeer)> channels,
        AlignmentReprocessor reprocessor,
        Dictionary<IAlignmentChannel, AlignmentOverride> alignment,
        double levelDifferenceDb,
        StringBuilder log)
    {
        IReadOnlyList<AlignmentSnapshot> snapshots = reprocessor.Reprocess(alignment);
        Dictionary<IAlignmentChannel, AlignmentSnapshot> byChannel = snapshots.ToDictionary(snapshot => snapshot.Channel);
        List<GainBalanceInput> inputs = channels
            .Select(item =>
            {
                (double lowHz, double highHz) = VirtualCrossoverJunctions.GetChannelBand(item.Settings);
                return new GainBalanceInput(
                    item.Channel,
                    byChannel[item.Channel].ImpulseResponse,
                    item.Channel.SampleRate,
                    item.Settings.GainDb,
                    lowHz,
                    highHz,
                    item.Settings.EffectiveCrossover.Kind != CrossoverKind.Off,
                    item.Mono,
                    item.RightSide,
                    item.LeftPeer);
            })
            .ToList();
        return GainBalanceEngine.Compute(inputs, levelDifferenceDb, log);
    }
}
