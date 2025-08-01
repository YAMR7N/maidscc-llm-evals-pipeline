# Daily Pipeline Automation Scripts

This document describes the automation scripts created to streamline your daily LLM pipeline operations.

## 📋 Overview

You now have two main automation scripts that handle your daily pipeline commands:

1. **`run_daily_pipeline.sh`** - Complete daily pipeline automation
2. **`run_pipeline_parts.sh`** - Individual component runner

## 🚀 Complete Daily Pipeline

### Usage
```bash
./run_daily_pipeline.sh
```

### What it does
Runs your complete daily pipeline in the optimal order with parallelization:

**Phase 1: Sentiment Analysis (All Departments)**
- Runs SA for all departments sequentially

**Phase 2: MV Resolvers (8 analyses in parallel)**
- FTR (xml3d format, gemini-2.5-pro)
- Categorizing (xml format, gemini-2.5-pro)
- False Promises (xml format, gemini-2.5-pro)
- Threatening Case (xml format, gemini-2.5-pro)
- Policy Escalation (xml format, gemini-2.5-pro)
- Legal Alignment (xml format, gemini-2.5-pro)
- Call Request (xml format, gemini-2.5-pro)
- Clarity Score (xml format, gemini-2.5-pro)

**Phase 3: Doctors (Sequential with dependencies)**
- Categorizing first (xml format, gemini-2.5-flash)
- Then Misprescription & Unnecessary Clinic Rec in parallel (xml format, gemini-2.5-flash)

### Features
- ✅ Automatic parallel execution where safe
- ✅ Proper dependency handling (Doctors categorizing → misprescription/clinic)
- ✅ All commands run with `--with-upload`
- ✅ Colored output with progress tracking
- ✅ Error handling and summary reporting

## 🔧 Individual Component Runner

### Usage
```bash
./run_pipeline_parts.sh [command]
```

### Available Commands

#### General Commands
- `sa` - Sentiment Analysis (all departments)

#### MV Resolvers Commands (all use gemini-2.5-pro)
- `mv-ftr` - FTR (xml3d format)
- `mv-categorizing` - Categorizing (xml format)
- `mv-false-promises` - False Promises (xml format)
- `mv-threatening` - Threatening Case (xml format)
- `mv-policy` - Policy Escalation (xml format)
- `mv-legal` - Legal Alignment (xml format)
- `mv-call` - Call Request (xml format)
- `mv-clarity` - Clarity Score (xml format)
- `mv-all` - All MV Resolvers (parallel)

#### Doctors Commands (all use gemini-2.5-flash, xml format)
- `docs-categorizing` - Categorizing (run first)
- `docs-misprescription` - Misprescription
- `docs-clinic` - Unnecessary Clinic Rec
- `docs-all` - All Doctors (sequential)

#### Combo Commands
- `mv-all docs-all` - Both MV Resolvers and Doctors
- `full` - Complete daily pipeline

### Examples
```bash
# Run just MV Resolvers FTR
./run_pipeline_parts.sh mv-ftr

# Run all MV Resolvers analyses
./run_pipeline_parts.sh mv-all

# Run Doctors categorizing first, then dependent analyses
./run_pipeline_parts.sh docs-all

# Run both MV Resolvers and Doctors
./run_pipeline_parts.sh mv-all docs-all
```

## 📊 Your Original Commands Mapped

### Before (Manual Commands)
```bash
# For all departments
python3 scripts/run_pipeline.py --prompt sentiment_analysis --departments "all" --with-upload

# For MV Resolvers (8 separate terminal commands)
python3 scripts/run_pipeline.py --prompt ftr --departments "MV Resolvers" --model gemini-2.5-pro --format xml3d --with-upload
python3 scripts/run_pipeline.py --prompt categorizing --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload
python3 scripts/run_pipeline.py --prompt false_promises --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload
python3 scripts/run_pipeline.py --prompt threatening --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload
python3 scripts/run_pipeline.py --prompt policy_escalation --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload
python3 scripts/run_pipeline.py --prompt legal_alignment --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload
python3 scripts/run_pipeline.py --prompt call_request --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload
python3 scripts/run_pipeline.py --prompt clarity_score --departments "MV Resolvers" --model gemini-2.5-pro --format xml --with-upload

# For Doctors (sequential)
python3 scripts/run_pipeline.py --prompt categorizing --departments "Doctors" --model gemini-2.5-flash --format xml --with-upload
python3 scripts/run_pipeline.py --prompt misprescription --departments "Doctors" --model gemini-2.5-flash --format xml --with-upload
python3 scripts/run_pipeline.py --prompt unnecessary_clinic_rec --departments "Doctors" --model gemini-2.5-flash --format xml --with-upload
```

### After (Automated)
```bash
# Single command for everything
./run_daily_pipeline.sh

# Or run parts individually
./run_pipeline_parts.sh sa
./run_pipeline_parts.sh mv-all
./run_pipeline_parts.sh docs-all
```

## 🎯 Benefits

1. **Time Saved**: One command instead of ~12 manual commands
2. **Parallel Execution**: MV Resolvers analyses run simultaneously
3. **Dependency Management**: Doctors categorizing runs before dependent analyses
4. **Error Handling**: Script continues even if individual analyses fail
5. **Clear Output**: Color-coded progress and status reporting
6. **Flexibility**: Can run individual components when needed

## 🛠️ Technical Details

- **Parallelization**: Uses bash background processes (`&`) and `wait`
- **Dependencies**: Sequential execution for Doctors (categorizing → others)
- **Error Handling**: Each phase reports success/failure independently
- **Settings**: All your model preferences and format specifications are hardcoded
- **Upload**: All commands automatically include `--with-upload`

## 📝 Notes

- The scripts automatically handle all your preferred models and formats
- Dependencies are properly managed (Doctors categorizing before misprescription/clinic)
- All commands run with upload enabled by default
- Scripts include help functions (`--help`) for reference 