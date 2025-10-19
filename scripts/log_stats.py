#!/usr/bin/env python3
"""
Log Statistics Generator
Analyzes RAG system logs and generates comprehensive statistics.

Usage:
    python scripts/log_stats.py [log_file]
    python scripts/log_stats.py                    # Analyzes most recent log
    python scripts/log_stats.py logs/rag_20250119.log  # Specific file
"""

import re
import sys
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

            if 'Retrieved' in line and 'documents in' in line:
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
    print("[LOG LEVELS SUMMARY]")
    print("-" * 70)
    total_logs = sum(stats['levels'].values())
    for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        count = stats['levels'].get(level, 0)
        pct = (count / total_logs * 100) if total_logs > 0 else 0
        print(f"  {level:10s}: {count:6d} ({pct:5.1f}%)")
    print(f"  {'TOTAL':10s}: {total_logs:6d}")
    print()

    # Performance metrics
    print("[PERFORMANCE METRICS]")
    print("-" * 70)

    if stats['api_times']:
        print(f"  API Generation Time:")
        print(f"    Count:   {len(stats['api_times'])}")
        print(f"    Average: {statistics.mean(stats['api_times']):.2f}s")
        print(f"    Median:  {statistics.median(stats['api_times']):.2f}s")
        print(f"    Min/Max: {min(stats['api_times']):.2f}s / {max(stats['api_times']):.2f}s")
        slow_count = sum(1 for t in stats['api_times'] if t > 5.0)
        if slow_count > 0:
            print(f"    [WARN] Slow calls (>5s): {slow_count}")
        print()

    if stats['retrieval_times']:
        print(f"  Retrieval Time:")
        print(f"    Count:   {len(stats['retrieval_times'])}")
        print(f"    Average: {statistics.mean(stats['retrieval_times']):.2f}s")
        print(f"    Median:  {statistics.median(stats['retrieval_times']):.2f}s")
        print(f"    Min/Max: {min(stats['retrieval_times']):.2f}s / {max(stats['retrieval_times']):.2f}s")
        slow_count = sum(1 for t in stats['retrieval_times'] if t > 2.0)
        if slow_count > 0:
            print(f"    [WARN] Slow retrievals (>2s): {slow_count}")
        print()

    if stats['eval_times']:
        print(f"  Evaluation Time:")
        print(f"    Count:   {len(stats['eval_times'])}")
        print(f"    Average: {statistics.mean(stats['eval_times']):.2f}s")
        print(f"    Median:  {statistics.median(stats['eval_times']):.2f}s")
        print(f"    Min/Max: {min(stats['eval_times']):.2f}s / {max(stats['eval_times']):.2f}s")
        slow_count = sum(1 for t in stats['eval_times'] if t > 20.0)
        if slow_count > 0:
            print(f"    [WARN] Slow evaluations (>20s): {slow_count}")
        print()

    if not (stats['api_times'] or stats['retrieval_times'] or stats['eval_times']):
        print("  No performance data found in logs")
        print()

    # Evaluation quality metrics
    print("[EVALUATION QUALITY METRICS]")
    print("-" * 70)

    if stats['faithfulness_scores']:
        avg_faith = statistics.mean(stats['faithfulness_scores'])
        print(f"  Faithfulness:")
        print(f"    Count:   {len(stats['faithfulness_scores'])}")
        print(f"    Average: {avg_faith:.4f}")
        print(f"    Median:  {statistics.median(stats['faithfulness_scores']):.4f}")
        print(f"    Min/Max: {min(stats['faithfulness_scores']):.4f} / {max(stats['faithfulness_scores']):.4f}")
        if avg_faith >= 0.9:
            status = "[OK] Excellent (>=0.9)"
        elif avg_faith >= 0.7:
            status = "[OK] Good (>=0.7)"
        elif avg_faith >= 0.5:
            status = "[WARN] Fair (>=0.5)"
        else:
            status = "[FAIL] Poor (<0.5)"
        print(f"    Status:  {status}")
        low_count = sum(1 for s in stats['faithfulness_scores'] if s < 0.7)
        if low_count > 0:
            print(f"    [WARN] Low scores (<0.7): {low_count}/{len(stats['faithfulness_scores'])}")
        print()

    if stats['relevancy_scores']:
        avg_relev = statistics.mean(stats['relevancy_scores'])
        print(f"  Answer Relevancy:")
        print(f"    Count:   {len(stats['relevancy_scores'])}")
        print(f"    Average: {avg_relev:.4f}")
        print(f"    Median:  {statistics.median(stats['relevancy_scores']):.4f}")
        print(f"    Min/Max: {min(stats['relevancy_scores']):.4f} / {max(stats['relevancy_scores']):.4f}")
        if avg_relev >= 0.9:
            status = "[OK] Excellent (>=0.9)"
        elif avg_relev >= 0.7:
            status = "[OK] Good (>=0.7)"
        elif avg_relev >= 0.5:
            status = "[WARN] Fair (>=0.5)"
        else:
            status = "[FAIL] Poor (<0.5)"
        print(f"    Status:  {status}")
        low_count = sum(1 for s in stats['relevancy_scores'] if s < 0.7)
        if low_count > 0:
            print(f"    [WARN] Low scores (<0.7): {low_count}/{len(stats['relevancy_scores'])}")
        print()

    if not (stats['faithfulness_scores'] or stats['relevancy_scores']):
        print("  No evaluation metrics found in logs")
        print()

    # Top active modules
    print("[TOP ACTIVE MODULES]")
    print("-" * 70)
    top_modules = sorted(stats['modules'].items(), key=lambda x: x[1], reverse=True)[:10]
    for module, count in top_modules:
        module_short = module if len(module) <= 45 else module[:42] + '...'
        print(f"  {module_short:48s}: {count:6d}")
    print()

    # Error summary
    print("[ERROR SUMMARY]")
    print("-" * 70)
    if stats['errors']:
        print(f"  Total Errors: {len(stats['errors'])}")
        error_rate = (len(stats['errors']) / total_logs * 100) if total_logs > 0 else 0
        print(f"  Error Rate:   {error_rate:.2f}%")

        if error_rate < 1:
            status = "[OK] Excellent (<1%)"
        elif error_rate < 5:
            status = "[OK] Good (<5%)"
        else:
            status = "[WARN] High (>=5%)"
        print(f"  Status:       {status}")
        print()

        if len(stats['errors']) > 0:
            print("  Most Recent Errors:")
            for i, error in enumerate(stats['errors'][-5:], 1):  # Last 5 errors
                # Extract just the error message
                parts = error.split('|')
                if len(parts) >= 4:
                    error_msg = parts[3].strip()
                else:
                    error_msg = error
                error_short = error_msg[:100] + '...' if len(error_msg) > 100 else error_msg
                print(f"    {i}. {error_short}")
    else:
        print(f"  Total Errors: 0")
        print(f"  Status:       [OK] No errors found!")

    print()
    print("=" * 70)


def main():
    """Main entry point."""

    # Determine log file to analyze
    if len(sys.argv) > 1:
        log_file = Path(sys.argv[1])
        if not log_file.exists():
            print(f"Error: Log file not found: {log_file}")
            sys.exit(1)
    else:
        # Find most recent log file
        log_dir = Path('logs')
        if not log_dir.exists():
            print("Error: logs/ directory not found!")
            print("Make sure you're running from the project root directory.")
            sys.exit(1)

        log_files = sorted(log_dir.glob('rag_*.log'), reverse=True)

        if not log_files:
            print("No log files found in logs/ directory!")
            sys.exit(1)

        log_file = log_files[0]

    print(f"Analyzing: {log_file}")
    print(f"File size: {log_file.stat().st_size / 1024:.1f} KB")
    print()

    # Analyze and report
    stats = analyze_logs(log_file)
    print_report(stats)


if __name__ == '__main__':
    main()
