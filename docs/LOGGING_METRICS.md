# Logging Metrics & Monitoring Guide

## Overview

This document provides standard metrics, analysis patterns, and monitoring strategies for the RAG Multi-Doc logging system.

## Table of Contents

1. [Key Performance Metrics](#key-performance-metrics)
2. [Log Analysis Commands](#log-analysis-commands)
3. [Error Tracking](#error-tracking)
4. [Performance Monitoring](#performance-monitoring)
5. [Standard Metrics Summary](#standard-metrics-summary)
6. [Automated Monitoring Scripts](#automated-monitoring-scripts)

---

## Key Performance Metrics

### 1. API Performance Metrics

**What to Track:**
- Average API response time
- API failure rate
- Token usage (if available)
- Request/response sizes

**Success Criteria:**
- ✅ Generation time < 5 seconds for most requests
- ✅ API failure rate < 1%
- ✅ Response sizes reasonable (< 5000 chars typically)

### 2. Retrieval Performance Metrics

**What to Track:**
- Average retrieval time per collection
- Total documents retrieved
- Retrieval success rate
- Top-N selection time

**Success Criteria:**
- ✅ Retrieval time < 2 seconds
- ✅ Consistent number of results (6-10 documents)
- ✅ No empty result sets for valid queries

### 3. Evaluation Metrics

**What to Track:**
- RAGAS execution time
- Faithfulness scores (target: > 0.7)
- Answer relevancy scores (target: > 0.7)
- Evaluation failure rate

**Success Criteria:**
- ✅ Faithfulness > 0.7 (70% factually accurate)
- ✅ Answer Relevancy > 0.7 (70% relevant)
- ✅ Evaluation time < 20 seconds
- ✅ Evaluation failure rate < 5%

### 4. System Health Metrics

**What to Track:**
- Error count per hour/day
- Warning count
- Critical failures
- Log file size growth

**Success Criteria:**
- ✅ Error rate < 5% of total operations
- ✅ No critical failures
- ✅ Log rotation working (files < 10MB)

---

## Log Analysis Commands

### Basic Log Analysis

```bash
# Count total log entries by level
grep -c "INFO" logs/rag_*.log
grep -c "WARNING" logs/rag_*.log
grep -c "ERROR" logs/rag_*.log

# View all errors today
grep "ERROR" logs/rag_$(date +%Y%m%d).log

# Count errors by type
grep "ERROR" logs/rag_*.log | cut -d'|' -f4 | sort | uniq -c | sort -rn

# Find slow operations (> 5 seconds)
grep "completed in" logs/rag_*.log | awk '{if ($NF > 5) print}'
```

### Performance Analysis

```bash
# Average API generation time
grep "Generation completed" logs/rag_*.log | \
  grep -oP 'in \K[0-9.]+' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "seconds"}'

# Average retrieval time
grep "Retrieved.*documents in" logs/rag_*.log | \
  grep -oP 'in \K[0-9.]+' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "seconds"}'

# Average evaluation time
grep "Evaluation completed" logs/rag_*.log | \
  grep -oP 'in \K[0-9.]+' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "seconds"}'
```

### Evaluation Metrics Analysis

```bash
# Extract faithfulness scores
grep "Results - Faithfulness" logs/rag_*.log | \
  grep -oP 'Faithfulness: \K[0-9.]+' | \
  awk '{sum+=$1; count++} END {print "Avg Faithfulness:", sum/count}'

# Extract answer relevancy scores
grep "Results - Faithfulness" logs/rag_*.log | \
  grep -oP 'Answer Relevancy: \K[0-9.]+' | \
  awk '{sum+=$1; count++} END {print "Avg Relevancy:", sum/count}'

# Count evaluations below threshold (< 0.7)
grep "Results - Faithfulness" logs/rag_*.log | \
  grep -oP 'Faithfulness: \K[0-9.]+' | \
  awk '{if ($1 < 0.7) count++} END {print "Low scores:", count}'
```

### Error Tracking

```bash
# Most common errors
grep "ERROR" logs/rag_*.log | \
  sed 's/.*ERROR.*|//' | \
  sort | uniq -c | sort -rn | head -10

# Errors by module
grep "ERROR" logs/rag_*.log | \
  cut -d'|' -f3 | \
  sort | uniq -c | sort -rn

# Timeline of errors (hourly)
grep "ERROR" logs/rag_*.log | \
  cut -d' ' -f1-2 | cut -d':' -f1 | \
  sort | uniq -c
```

---

## Error Tracking

### Error Categories

1. **API Errors** - Google API failures, timeout, rate limits
2. **Database Errors** - ChromaDB connection, query failures
3. **Validation Errors** - Schema validation, data format issues
4. **System Errors** - File I/O, permission issues

### Critical Error Patterns to Monitor

```bash
# API failures
grep -i "api.*fail\|timeout\|rate limit" logs/errors.log

# Database errors
grep -i "chroma\|database\|connection" logs/errors.log

# Validation errors
grep -i "validation\|schema.*fail" logs/errors.log

# Out of memory or resource issues
grep -i "memory\|resource" logs/errors.log
```

---

## Performance Monitoring

### Daily Performance Report

Create a simple daily report script:

```bash
#!/bin/bash
# daily_report.sh

LOG_FILE="logs/rag_$(date +%Y%m%d).log"
echo "=== Daily Performance Report $(date +%Y-%m-%d) ==="
echo ""

# Total operations
echo "## Operations Summary"
echo "Total INFO logs: $(grep -c 'INFO' $LOG_FILE)"
echo "Total WARNINGS:  $(grep -c 'WARNING' $LOG_FILE)"
echo "Total ERRORS:    $(grep -c 'ERROR' $LOG_FILE)"
echo ""

# Average timings
echo "## Performance Metrics"
echo "Avg API time:     $(grep 'Generation completed' $LOG_FILE | grep -oP 'in \K[0-9.]+' | awk '{sum+=$1; n++} END {if (n>0) print sum/n "s"; else print "N/A"}')"
echo "Avg Retrieval:    $(grep 'Retrieved.*documents in' $LOG_FILE | grep -oP 'in \K[0-9.]+' | awk '{sum+=$1; n++} END {if (n>0) print sum/n "s"; else print "N/A"}')"
echo "Avg Evaluation:   $(grep 'Evaluation completed' $LOG_FILE | grep -oP 'in \K[0-9.]+' | awk '{sum+=$1; n++} END {if (n>0) print sum/n "s"; else print "N/A"}')"
echo ""

# Evaluation scores
echo "## Evaluation Metrics"
echo "Avg Faithfulness: $(grep 'Results - Faithfulness' $LOG_FILE | grep -oP 'Faithfulness: \K[0-9.]+' | awk '{sum+=$1; n++} END {if (n>0) printf "%.4f", sum/n; else print "N/A"}')"
echo "Avg Relevancy:    $(grep 'Results - Faithfulness' $LOG_FILE | grep -oP 'Answer Relevancy: \K[0-9.]+' | awk '{sum+=$1; n++} END {if (n>0) printf "%.4f", sum/n; else print "N/A"}')"
echo ""

# Top errors
echo "## Top Errors (if any)"
grep 'ERROR' $LOG_FILE | sed 's/.*ERROR.*|//' | sort | uniq -c | sort -rn | head -5
```

Usage:
```bash
chmod +x daily_report.sh
./daily_report.sh
```

---

## Standard Metrics Summary

### Performance Benchmarks

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| API Response Time | < 3s | 3-5s | > 5s |
| Retrieval Time | < 1.5s | 1.5-3s | > 3s |
| Evaluation Time | < 15s | 15-25s | > 25s |
| Faithfulness Score | > 0.8 | 0.6-0.8 | < 0.6 |
| Answer Relevancy | > 0.8 | 0.6-0.8 | < 0.6 |
| Error Rate | < 1% | 1-5% | > 5% |

### Quality Metrics (RAGAS)

**Faithfulness (Factual Accuracy)**
- 0.9-1.0: Excellent - Answer fully supported by context
- 0.7-0.9: Good - Mostly accurate, minor unsupported claims
- 0.5-0.7: Fair - Some hallucinations or unsupported statements
- < 0.5: Poor - Significant hallucinations

**Answer Relevancy**
- 0.9-1.0: Excellent - Directly answers the question
- 0.7-0.9: Good - Relevant with minor tangents
- 0.5-0.7: Fair - Partially relevant
- < 0.5: Poor - Off-topic or incomplete

---

## Automated Monitoring Scripts

### 1. Real-time Error Monitor

```bash
#!/bin/bash
# error_monitor.sh - Watch for errors in real-time

tail -f logs/rag_*.log | grep --line-buffered "ERROR" | \
while read line; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR DETECTED:"
    echo "$line"
    echo "---"
done
```

### 2. Performance Threshold Alert

```bash
#!/bin/bash
# perf_alert.sh - Alert on slow operations

tail -f logs/rag_*.log | grep --line-buffered "completed in" | \
while read line; do
    time=$(echo "$line" | grep -oP 'in \K[0-9.]+')
    if (( $(echo "$time > 5.0" | bc -l) )); then
        echo "⚠️  SLOW OPERATION DETECTED: $time seconds"
        echo "$line"
        echo "---"
    fi
done
```

### 3. Evaluation Quality Monitor

```bash
#!/bin/bash
# quality_monitor.sh - Monitor evaluation scores

tail -f logs/rag_*.log | grep --line-buffered "Results - Faithfulness" | \
while read line; do
    faith=$(echo "$line" | grep -oP 'Faithfulness: \K[0-9.]+')
    relev=$(echo "$line" | grep -oP 'Answer Relevancy: \K[0-9.]+')

    if (( $(echo "$faith < 0.7" | bc -l) )); then
        echo "⚠️  LOW FAITHFULNESS: $faith"
        echo "$line"
    fi

    if (( $(echo "$relev < 0.7" | bc -l) )); then
        echo "⚠️  LOW RELEVANCY: $relev"
        echo "$line"
    fi
done
```

### 4. Log Statistics Generator (Python)

```python
#!/usr/bin/env python3
# log_stats.py - Generate comprehensive log statistics

import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import statistics

def analyze_logs(log_file):
    """Analyze log file and generate statistics."""

    stats = {
        'levels': defaultdict(int),
        'modules': defaultdict(int),
        'errors': [],
        'api_times': [],
        'retrieval_times': [],
        'eval_times': [],
        'faithfulness_scores': [],
        'relevancy_scores': []
    }

    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Count log levels
            for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                if f'| {level}' in line:
                    stats['levels'][level] += 1
                    break

            # Track modules
            match = re.search(r'\| ([a-zA-Z0-9_.]+) \|', line)
            if match:
                stats['modules'][match.group(1)] += 1

            # Extract timing metrics
            if 'Generation completed in' in line:
                time = re.search(r'in (\d+\.\d+)s', line)
                if time:
                    stats['api_times'].append(float(time.group(1)))

            if 'Retrieved.*documents in' in line:
                time = re.search(r'in (\d+\.\d+)s', line)
                if time:
                    stats['retrieval_times'].append(float(time.group(1)))

            if 'Evaluation completed in' in line:
                time = re.search(r'in (\d+\.\d+)s', line)
                if time:
                    stats['eval_times'].append(float(time.group(1)))

            # Extract evaluation scores
            if 'Results - Faithfulness' in line:
                faith = re.search(r'Faithfulness: (\d+\.\d+)', line)
                relev = re.search(r'Answer Relevancy: (\d+\.\d+)', line)
                if faith:
                    stats['faithfulness_scores'].append(float(faith.group(1)))
                if relev:
                    stats['relevancy_scores'].append(float(relev.group(1)))

            # Collect errors
            if 'ERROR' in line:
                stats['errors'].append(line.strip())

    return stats

def print_report(stats):
    """Print formatted statistics report."""

    print("=" * 70)
    print(f"LOG ANALYSIS REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # Log levels summary
    print("📊 LOG LEVELS SUMMARY")
    print("-" * 70)
    total_logs = sum(stats['levels'].values())
    for level, count in sorted(stats['levels'].items()):
        pct = (count / total_logs * 100) if total_logs > 0 else 0
        print(f"  {level:10s}: {count:6d} ({pct:5.1f}%)")
    print(f"  {'TOTAL':10s}: {total_logs:6d}")
    print()

    # Performance metrics
    print("⚡ PERFORMANCE METRICS")
    print("-" * 70)

    if stats['api_times']:
        print(f"  API Generation Time:")
        print(f"    Average: {statistics.mean(stats['api_times']):.2f}s")
        print(f"    Median:  {statistics.median(stats['api_times']):.2f}s")
        print(f"    Min/Max: {min(stats['api_times']):.2f}s / {max(stats['api_times']):.2f}s")
        print()

    if stats['retrieval_times']:
        print(f"  Retrieval Time:")
        print(f"    Average: {statistics.mean(stats['retrieval_times']):.2f}s")
        print(f"    Median:  {statistics.median(stats['retrieval_times']):.2f}s")
        print(f"    Min/Max: {min(stats['retrieval_times']):.2f}s / {max(stats['retrieval_times']):.2f}s")
        print()

    if stats['eval_times']:
        print(f"  Evaluation Time:")
        print(f"    Average: {statistics.mean(stats['eval_times']):.2f}s")
        print(f"    Median:  {statistics.median(stats['eval_times']):.2f}s")
        print(f"    Min/Max: {min(stats['eval_times']):.2f}s / {max(stats['eval_times']):.2f}s")
        print()

    # Evaluation quality metrics
    print("🎯 EVALUATION QUALITY METRICS")
    print("-" * 70)

    if stats['faithfulness_scores']:
        avg_faith = statistics.mean(stats['faithfulness_scores'])
        print(f"  Faithfulness:")
        print(f"    Average: {avg_faith:.4f}")
        print(f"    Median:  {statistics.median(stats['faithfulness_scores']):.4f}")
        print(f"    Min/Max: {min(stats['faithfulness_scores']):.4f} / {max(stats['faithfulness_scores']):.4f}")
        status = "✅ Excellent" if avg_faith > 0.8 else "⚠️  Needs Improvement"
        print(f"    Status:  {status}")
        print()

    if stats['relevancy_scores']:
        avg_relev = statistics.mean(stats['relevancy_scores'])
        print(f"  Answer Relevancy:")
        print(f"    Average: {avg_relev:.4f}")
        print(f"    Median:  {statistics.median(stats['relevancy_scores']):.4f}")
        print(f"    Min/Max: {min(stats['relevancy_scores']):.4f} / {max(stats['relevancy_scores']):.4f}")
        status = "✅ Excellent" if avg_relev > 0.8 else "⚠️  Needs Improvement"
        print(f"    Status:  {status}")
        print()

    # Top active modules
    print("📦 TOP ACTIVE MODULES")
    print("-" * 70)
    top_modules = sorted(stats['modules'].items(), key=lambda x: x[1], reverse=True)[:10]
    for module, count in top_modules:
        print(f"  {module:50s}: {count:6d}")
    print()

    # Error summary
    if stats['errors']:
        print("❌ ERROR SUMMARY")
        print("-" * 70)
        print(f"  Total Errors: {len(stats['errors'])}")
        error_rate = (len(stats['errors']) / total_logs * 100) if total_logs > 0 else 0
        print(f"  Error Rate:   {error_rate:.2f}%")
        print()
        print("  Recent Errors:")
        for error in stats['errors'][-5:]:  # Last 5 errors
            print(f"    {error[:100]}...")

    print("=" * 70)

if __name__ == '__main__':
    import sys

    log_dir = Path('logs')

    # Find most recent log file
    log_files = sorted(log_dir.glob('rag_*.log'), reverse=True)

    if not log_files:
        print("No log files found!")
        sys.exit(1)

    log_file = log_files[0]
    print(f"Analyzing: {log_file}")
    print()

    stats = analyze_logs(log_file)
    print_report(stats)
```

Usage:
```bash
chmod +x log_stats.py
python log_stats.py
```

---

## Summary Checklist

### Daily Monitoring

- [ ] Check error log: `cat logs/errors.log`
- [ ] Review error rate: Should be < 5%
- [ ] Check average response times
- [ ] Review evaluation scores (faithfulness & relevancy)
- [ ] Verify log rotation is working

### Weekly Analysis

- [ ] Run `log_stats.py` for comprehensive report
- [ ] Compare metrics week-over-week
- [ ] Identify performance trends
- [ ] Review any recurring errors
- [ ] Check disk space for log files

### Monthly Review

- [ ] Archive old logs
- [ ] Update performance baselines
- [ ] Review and adjust alert thresholds
- [ ] Document any system improvements
- [ ] Clean up rotated log files (older than 30 days)

---

## Key Takeaways

1. **Performance Targets**: API < 5s, Retrieval < 2s, Evaluation < 20s
2. **Quality Targets**: Faithfulness > 0.7, Relevancy > 0.7
3. **Health Targets**: Error rate < 5%, No critical failures
4. **Monitoring**: Daily error checks, weekly performance reports
5. **Automation**: Use provided scripts for continuous monitoring

For questions or issues with metrics interpretation, refer to the main [LOGGING.md](./LOGGING.md) documentation.
