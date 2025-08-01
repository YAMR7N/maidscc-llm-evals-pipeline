#!/bin/bash

# Daily LLM Pipeline Runner
# Organizes and runs all daily analysis commands with proper parallelization and dependencies

set -e  # Exit on any error

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
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
run_pipeline() {
    local prompt="$1"
    local departments="$2"
    local model="$3"
    local format="$4"
    local extra_args="$5"
    
    local cmd="python3 scripts/run_pipeline.py --prompt $prompt --departments \"$departments\" --with-upload"
    
    if [ -n "$model" ]; then
        cmd="$cmd --model $model"
    fi
    
    if [ -n "$format" ]; then
        cmd="$cmd --format $format"
    fi
    
    if [ -n "$extra_args" ]; then
        cmd="$cmd $extra_args"
    fi
    
    log "Running: $prompt for $departments"
    echo "Command: $cmd"
    eval $cmd
    
    if [ $? -eq 0 ]; then
        success "$prompt completed for $departments"
    else
        error "$prompt failed for $departments"
        return 1
    fi
}

# Function to run commands in parallel
run_parallel() {
    local commands=("$@")
    local pids=()
    
    # Start all commands in background
    for cmd in "${commands[@]}"; do
        eval "$cmd" &
        pids+=($!)
    done
    
    # Wait for all to complete
    local failed=0
    for pid in "${pids[@]}"; do
        if ! wait $pid; then
            failed=1
        fi
    done
    
    return $failed
}

# Main execution starts here
main() {
    section "🚀 Starting Daily LLM Pipeline"
    
    # Phase 1: Sentiment Analysis for All Departments (skip if requested)
    if [ "$SKIP_SA" = false ]; then
        section "📊 Phase 1: Sentiment Analysis (All Departments)"
        run_pipeline "sentiment_analysis" "all" "" "" ""
    else
        log "⏭️ Skipping Phase 1: Sentiment Analysis"
    fi
    
    # Phase 2: MV Resolvers Analysis (Parallel Execution)
    section "🏢 Phase 2: MV Resolvers Analysis (Parallel)"
    
    # Prepare MV Resolvers commands for parallel execution
    mv_commands=(
        "run_pipeline 'ftr' 'MV Resolvers' 'gemini-2.5-pro' 'xml3d' ''"
        "run_pipeline 'categorizing' 'MV Resolvers' 'gemini-2.5-pro' 'xml' ''"
        "run_pipeline 'false_promises' 'MV Resolvers' 'gemini-2.5-pro' 'xml' ''"
        "run_pipeline 'threatening' 'MV Resolvers' 'gemini-2.5-pro' 'xml' ''"
        "run_pipeline 'policy_escalation' 'MV Resolvers' 'gemini-2.5-pro' 'xml' ''"
        "run_pipeline 'legal_alignment' 'MV Resolvers' 'gemini-2.5-pro' 'xml' ''"
        "run_pipeline 'call_request' 'MV Resolvers' 'gemini-2.5-pro' 'xml' ''"
        "run_pipeline 'clarity_score' 'MV Resolvers' 'gemini-2.5-pro' 'xml' ''"
    )
    
    # Execute MV Resolvers commands in parallel
    log "Starting ${#mv_commands[@]} MV Resolvers analyses in parallel..."
    
    pids=()
    for cmd in "${mv_commands[@]}"; do
        eval "$cmd" &
        pids+=($!)
    done
    
    # Wait for all MV Resolvers analyses to complete
    mv_failed=0
    for pid in "${pids[@]}"; do
        if ! wait $pid; then
            mv_failed=1
        fi
    done
    
    if [ $mv_failed -eq 0 ]; then
        success "All MV Resolvers analyses completed successfully"
    else
        warning "Some MV Resolvers analyses failed"
    fi
    
    # Phase 3: Doctors Analysis (Sequential Dependencies)
    section "👩‍⚕️ Phase 3: Doctors Analysis (Sequential Dependencies)"
    
    # Step 3.1: Categorizing (must run first)
    log "Step 3.1: Running categorizing for Doctors (dependency for other analyses)"
    run_pipeline "categorizing" "Doctors" "gemini-2.5-flash" "xml" ""
    
    if [ $? -eq 0 ]; then
        success "Doctors categorizing completed successfully"
        
        # Step 3.2: Misprescription and Unnecessary Clinic Rec (parallel, depend on categorizing)
        log "Step 3.2: Running misprescription and unnecessary clinic rec in parallel"
        
        doctors_dependent_commands=(
            "run_pipeline 'misprescription' 'Doctors' 'gemini-2.5-flash' 'xml' ''"
            "run_pipeline 'unnecessary_clinic_rec' 'Doctors' 'gemini-2.5-flash' 'xml' ''"
        )
        
        doctors_pids=()
        for cmd in "${doctors_dependent_commands[@]}"; do
            eval "$cmd" &
            doctors_pids+=($!)
        done
        
        # Wait for dependent analyses to complete
        doctors_failed=0
        for pid in "${doctors_pids[@]}"; do
            if ! wait $pid; then
                doctors_failed=1
            fi
        done
        
        if [ $doctors_failed -eq 0 ]; then
            success "All Doctors analyses completed successfully"
        else
            warning "Some Doctors analyses failed"
        fi
    else
        error "Doctors categorizing failed - skipping dependent analyses"
    fi
    
    # Final Summary
    section "📈 Pipeline Execution Summary"
    
    local total_failed=$((mv_failed + doctors_failed))
    
    if [ $total_failed -eq 0 ]; then
        success "🎉 All daily pipeline analyses completed successfully!"
        success "✨ Ready for data review and insights"
    else
        warning "⚠️  Some analyses failed. Please check the logs above for details."
        warning "🔧 You may need to rerun failed analyses manually"
    fi
    
    log "Daily pipeline execution completed at $(date)"
}

# Help function
show_help() {
    echo "Daily LLM Pipeline Runner"
    echo ""
    echo "This script runs your daily analysis pipeline with proper dependencies and parallelization:"
    echo ""
    echo "Phase 1: Sentiment Analysis (All Departments)"
    echo "Phase 2: MV Resolvers (8 analyses in parallel)"
    echo "  - FTR, Categorizing, False Promises, Threatening Case"
    echo "  - Policy Escalation, Legal Alignment, Call Request, Clarity Score"
    echo "Phase 3: Doctors (Sequential with dependencies)"
    echo "  - Categorizing (first)"
    echo "  - Misprescription & Unnecessary Clinic Rec (parallel, after categorizing)"
    echo ""
    echo "Usage:"
    echo "  ./run_daily_pipeline.sh           Run the full daily pipeline"
    echo "  ./run_daily_pipeline.sh --skip-sa Run pipeline starting after SA"
    echo "  ./run_daily_pipeline.sh --help    Show this help message"
    echo ""
    echo "All commands run with --with-upload enabled"
    echo "Models and formats are automatically set per your specifications"
}

# Check command line arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

# Check for skip-sa option
SKIP_SA=false
if [ "$1" = "--skip-sa" ]; then
    SKIP_SA=true
    section "⏭️ Skipping Sentiment Analysis as requested"
fi

# Export the run_pipeline function so it can be used in subshells
export -f run_pipeline
export -f log
export -f success
export -f warning
export -f error

# Run the main pipeline
main

# Exit with success
exit 0 