#!/bin/bash

# Individual Pipeline Component Runner
# Helper script for running specific parts of your daily pipeline

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

section() {
    echo -e "\n${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}🔄 $1${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Function to run a pipeline command
run_cmd() {
    local prompt="$1"
    local departments="$2"
    local model="$3"
    local format="$4"
    
    local cmd="python3 scripts/run_pipeline.py --prompt $prompt --departments \"$departments\" --with-upload"
    
    if [ -n "$model" ]; then
        cmd="$cmd --model $model"
    fi
    
    if [ -n "$format" ]; then
        cmd="$cmd --format $format"
    fi
    
    log "Running: $cmd"
    eval $cmd
}

# Show help
show_help() {
    echo "Individual Pipeline Component Runner"
    echo ""
    echo "Quick commands for your daily pipeline components:"
    echo ""
    echo "📊 General Commands:"
    echo "  ./run_pipeline_parts.sh sa                    # Sentiment Analysis (all departments)"
    echo ""
    echo "🏢 MV Resolvers Commands (all use gemini-2.5-pro):"
    echo "  ./run_pipeline_parts.sh mv-ftr               # FTR (xml3d format)"
    echo "  ./run_pipeline_parts.sh mv-categorizing      # Categorizing (xml format)"
    echo "  ./run_pipeline_parts.sh mv-false-promises    # False Promises (xml format)"
    echo "  ./run_pipeline_parts.sh mv-threatening       # Threatening Case (xml format)"
    echo "  ./run_pipeline_parts.sh mv-policy            # Policy Escalation (xml format)"
    echo "  ./run_pipeline_parts.sh mv-legal             # Legal Alignment (xml format)"
    echo "  ./run_pipeline_parts.sh mv-call              # Call Request (xml format)"
    echo "  ./run_pipeline_parts.sh mv-clarity           # Clarity Score (xml format)"
    echo "  ./run_pipeline_parts.sh mv-all               # All MV Resolvers (parallel)"
    echo ""
    echo "👩‍⚕️ Doctors Commands (all use gemini-2.5-flash, xml format):"
    echo "  ./run_pipeline_parts.sh docs-categorizing    # Categorizing (run first)"
    echo "  ./run_pipeline_parts.sh docs-misprescription # Misprescription"
    echo "  ./run_pipeline_parts.sh docs-clinic          # Unnecessary Clinic Rec"
    echo "  ./run_pipeline_parts.sh docs-all             # All Doctors (sequential)"
    echo ""
    echo "🚀 Combo Commands:"
    echo "  ./run_pipeline_parts.sh mv-all docs-all      # Both MV Resolvers and Doctors"
    echo "  ./run_pipeline_parts.sh full                 # Complete daily pipeline"
    echo ""
    echo "❓ Help:"
    echo "  ./run_pipeline_parts.sh --help               # Show this help"
}

# Main execution
case "$1" in
    # General commands
    "sa")
        section "📊 Sentiment Analysis (All Departments)"
        run_cmd "sentiment_analysis" "all" "" ""
        ;;
    
    # MV Resolvers commands
    "mv-ftr")
        section "📈 MV Resolvers: FTR Analysis"
        run_cmd "ftr" "MV Resolvers" "gemini-2.5-pro" "xml3d"
        ;;
    "mv-categorizing")
        section "📂 MV Resolvers: Categorizing Analysis"
        run_cmd "categorizing" "MV Resolvers" "gemini-2.5-pro" "xml"
        ;;
    "mv-false-promises")
        section "🔍 MV Resolvers: False Promises Analysis"
        run_cmd "false_promises" "MV Resolvers" "gemini-2.5-pro" "xml"
        ;;
    "mv-threatening")
        section "⚠️ MV Resolvers: Threatening Case Analysis"
        run_cmd "threatening" "MV Resolvers" "gemini-2.5-pro" "xml"
        ;;
    "mv-policy")
        section "⚖️ MV Resolvers: Policy Escalation Analysis"
        run_cmd "policy_escalation" "MV Resolvers" "gemini-2.5-pro" "xml"
        ;;
    "mv-legal")
        section "⚖️ MV Resolvers: Legal Alignment Analysis"
        run_cmd "legal_alignment" "MV Resolvers" "gemini-2.5-pro" "xml"
        ;;
    "mv-call")
        section "📞 MV Resolvers: Call Request Analysis"
        run_cmd "call_request" "MV Resolvers" "gemini-2.5-pro" "xml"
        ;;
    "mv-clarity")
        section "🔍 MV Resolvers: Clarity Score Analysis"
        run_cmd "clarity_score" "MV Resolvers" "gemini-2.5-pro" "xml"
        ;;
    "mv-all")
        section "🏢 MV Resolvers: All Analyses (Parallel)"
        log "Starting 8 MV Resolvers analyses in parallel..."
        
        # Run all MV Resolvers commands in parallel
        python3 scripts/run_pipeline.py --prompt ftr --departments "MV Resolvers" --model gemini-2.5-pro --format xml3d --with-upload &
        python3 scripts/run_pipeline.py --prompt categorizing --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload &
        python3 scripts/run_pipeline.py --prompt false_promises --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload &
        python3 scripts/run_pipeline.py --prompt threatening --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload &
        python3 scripts/run_pipeline.py --prompt policy_escalation --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload &
        python3 scripts/run_pipeline.py --prompt legal_alignment --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload &
        python3 scripts/run_pipeline.py --prompt call_request --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload &
        python3 scripts/run_pipeline.py --prompt clarity_score --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload &
        
        # Wait for all to complete
        wait
        success "All MV Resolvers analyses completed"
        ;;
    
    # Doctors commands
    "docs-categorizing")
        section "👩‍⚕️ Doctors: Categorizing Analysis"
        run_cmd "categorizing" "Doctors" "gemini-2.5-flash" "xml"
        ;;
    "docs-misprescription")
        section "💊 Doctors: Misprescription Analysis"
        run_cmd "misprescription" "Doctors" "gemini-2.5-flash" "xml"
        ;;
    "docs-clinic")
        section "🏥 Doctors: Unnecessary Clinic Rec Analysis"
        run_cmd "unnecessary_clinic_rec" "Doctors" "gemini-2.5-flash" "xml"
        ;;
    "docs-all")
        section "👩‍⚕️ Doctors: All Analyses (Sequential)"
        log "Step 1: Running categorizing (dependency)"
        run_cmd "categorizing" "Doctors" "gemini-2.5-flash" "xml"
        
        log "Step 2: Running dependent analyses in parallel"
        python3 scripts/run_pipeline.py --prompt misprescription --departments "Doctors" --model gemini-2.5-flash --format xml --with-upload &
        python3 scripts/run_pipeline.py --prompt unnecessary_clinic_rec --departments "Doctors" --model gemini-2.5-flash --format xml --with-upload &
        
        wait
        success "All Doctors analyses completed"
        ;;
    
    # Combo commands
    "full")
        section "🚀 Complete Daily Pipeline"
        ./run_daily_pipeline.sh
        ;;
    
    # Handle multiple arguments (e.g., mv-all docs-all)
    *)
        if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ -z "$1" ]; then
            show_help
        else
            # Check if multiple commands provided
            for arg in "$@"; do
                case "$arg" in
                    "mv-all"|"docs-all"|"sa")
                        section "🔄 Running: $arg"
                        "$0" "$arg"
                        ;;
                    *)
                        echo "Unknown command: $arg"
                        echo "Use --help to see available commands"
                        exit 1
                        ;;
                esac
            done
        fi
        ;;
esac 