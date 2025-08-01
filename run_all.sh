#!/bin/bash
# Universal LLM-as-a-Judge Pipeline Runner
set -e

echo "🚀 Universal LLM-as-a-Judge Pipeline Runner"
echo "📅 $(date)"

show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
echo "  sa                 Run sentiment analysis (default: all departments, segmented)"
echo "  rb                 Run rule breaking analysis (default: available departments, json)"
echo "  ftr                Run FTR analysis (default: all departments, transparent)"
echo "  false_promises     Run false promises analysis (requires system prompts, json)"
echo "  categorizing       Run category docs analysis (gpt-4o, xml)"
echo "  policy_escalation  Run policy escalation analysis (requires system prompts, xml)"
echo "  client_suspecting_ai  Run client suspecting AI analysis (gemini-2.5-pro, json)"
echo "  clarity_score      Run clarity score analysis (gemini-2.5-pro, xml)"
echo "  legal_alignment    Run legal alignment analysis (gemini-2.5-pro, xml)"
echo "  call_request       Run call request analysis (gemini-2.5-pro, xml)"
echo "  threatening        Run threatening analysis (gemini-2.5-pro, segmented)"
echo "  misprescription    Run misprescription analysis (gemini-2.5-flash, depends on categorizing)"
echo "  unnecessary_clinic_rec Run unnecessary clinic rec analysis (gemini-2.5-flash, depends on categorizing)"
    echo ""
    echo "Options:"
    echo "  --departments DEPTS    Comma-separated departments or 'all'"
    echo "  --model MODEL         Model to use (default: gpt-4o for SA/FTR/categorizing, o4-mini for RB, gemini-2.5-pro for false_promises/policy_escalation/client_suspecting_ai/clarity_score/legal_alignment/call_request/threatening, gemini-2.5-flash for misprescription/unnecessary_clinic_rec)"
    echo "  --format FORMAT       Data format (segmented, json, xml, xml3d, transparent)"
    echo "  --with-upload         Include post-processing and upload (generates summary reports)"
    echo "  --dry-run            Show what would run without executing"
    echo ""
    echo "Examples:"
echo "  $0 sa --with-upload                      # Full SA pipeline"  
echo "  $0 rb --departments \"Doctors,CC Sales\"   # Rule breaking for specific depts"
echo "  $0 false_promises --departments \"MV Resolvers\" # False promises analysis"
echo "  $0 categorizing --departments \"MV Resolvers\"   # Category docs analysis"
echo "  $0 policy_escalation --departments \"MV Resolvers\" # Policy escalation analysis"
echo "  $0 client_suspecting_ai --departments \"MV Resolvers\" # Client suspecting AI analysis"
echo "  $0 clarity_score --departments \"MV Resolvers\" # Clarity score analysis"
echo "  $0 legal_alignment --departments \"MV Resolvers\" # Legal alignment analysis"
echo "  $0 call_request --departments \"MV Resolvers\" # Call request analysis"
echo "  $0 threatening --departments \"MV Resolvers\" # Threatening analysis"
echo "  $0 misprescription --departments \"Doctors\" # Misprescription analysis (requires categorizing first)"
echo "  $0 unnecessary_clinic_rec --departments \"Doctors\" # Unnecessary clinic rec analysis (requires categorizing first)"
echo "  $0 categorizing --format xml3d --departments \"MV Resolvers\" # Multi-day customer view"
echo "  $0 ftr                                   # FTR analysis"
}

COMMAND=""
DEPARTMENTS="all"
MODEL=""
FORMAT=""
WITH_UPLOAD=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        sa|rb|ftr|false_promises|categorizing|policy_escalation|client_suspecting_ai|clarity_score|legal_alignment|call_request|threatening|misprescription|unnecessary_clinic_rec) COMMAND="$1"; shift ;;
        --departments) DEPARTMENTS="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --format) FORMAT="$2"; shift 2 ;;
        --with-upload) WITH_UPLOAD=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help) show_help; exit 0 ;;
        *) echo "❌ Unknown option: $1"; show_help; exit 1 ;;
    esac
done

if [[ -z "$COMMAND" ]]; then
    echo "ℹ️  No command specified. Use --help for options."
    echo "🎯 Quick start: $0 sa --with-upload"
    exit 1
fi

case $COMMAND in
    sa) PROMPT="sentiment_analysis"; MODEL="${MODEL:-gpt-4o}"; FORMAT="${FORMAT:-segmented}" ;;
    rb) PROMPT="rule_breaking"; MODEL="${MODEL:-o4-mini}"; FORMAT="${FORMAT:-json}" ;;
    ftr) PROMPT="ftr"; MODEL="${MODEL:-gpt-4o}"; FORMAT="${FORMAT:-transparent}" ;;
    false_promises) PROMPT="false_promises"; MODEL="${MODEL:-gemini-2.5-pro}"; FORMAT="${FORMAT:-json}" ;;
    categorizing) PROMPT="categorizing"; MODEL="${MODEL:-gpt-4o}"; FORMAT="${FORMAT:-xml}" ;;
    policy_escalation) PROMPT="policy_escalation"; MODEL="${MODEL:-gemini-2.5-pro}"; FORMAT="${FORMAT:-xml}" ;;
    client_suspecting_ai) PROMPT="client_suspecting_ai"; MODEL="${MODEL:-gemini-2.5-pro}"; FORMAT="${FORMAT:-json}" ;;
    clarity_score) PROMPT="clarity_score"; MODEL="${MODEL:-gemini-2.5-pro}"; FORMAT="${FORMAT:-xml}" ;;
    legal_alignment) PROMPT="legal_alignment"; MODEL="${MODEL:-gemini-2.5-pro}"; FORMAT="${FORMAT:-xml}" ;;
    call_request) PROMPT="call_request"; MODEL="${MODEL:-gemini-2.5-pro}"; FORMAT="${FORMAT:-xml}" ;;
    threatening) PROMPT="threatening"; MODEL="${MODEL:-gemini-2.5-pro}"; FORMAT="${FORMAT:-segmented}" ;;
misprescription) PROMPT="misprescription"; MODEL="${MODEL:-gemini-2.5-flash}"; FORMAT="${FORMAT:-xml}" ;;
unnecessary_clinic_rec) PROMPT="unnecessary_clinic_rec"; MODEL="${MODEL:-gemini-2.5-flash}"; FORMAT="${FORMAT:-xml}" ;;
esac

CMD="python3 scripts/run_pipeline.py --prompt $PROMPT --departments \"$DEPARTMENTS\" --format $FORMAT --model $MODEL"
[[ "$WITH_UPLOAD" == true ]] && CMD="$CMD --with-upload"
[[ "$DRY_RUN" == true ]] && CMD="$CMD --dry-run"

echo "📋 Running: $COMMAND with $MODEL on $DEPARTMENTS"
echo "🚀 Executing: $CMD"
echo ""

eval $CMD

if [ $? -eq 0 ]; then
    echo "🎉 Pipeline completed successfully!"
else
    echo "❌ Pipeline failed!"
    exit 1
fi
