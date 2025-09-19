#!/usr/bin/env python3
"""
Simple script to plot etcd benchmark results
"""

import json
import glob
import matplotlib.pyplot as plt
import numpy as np
import re
import argparse
from pathlib import Path

def extract_node_count(filename):
    """Extract node count from filename like 'results-3nodes.json'"""
    match = re.search(r'results-(\d+)nodes?\.json', filename)
    if match:
        return int(match.group(1))
    return None

def load_results(pattern="results-*nodes*.json"):
    """Load all benchmark result files matching the pattern"""
    results = {}
    
    files = glob.glob(pattern)
    if not files:
        print(f"No files found matching pattern: {pattern}")
        return results
    
    for file in files:
        node_count = extract_node_count(file)
        if node_count is None:
            print(f"Could not extract node count from: {file}")
            continue
            
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                results[node_count] = data
                print(f"Loaded results for {node_count} nodes from {file}")
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    return results

def create_performance_plots(results):
    """Create comprehensive performance plots"""
    if not results:
        print("No results to plot")
        return
    
    # Sort by node count
    node_counts = sorted(results.keys())
    
    # Extract metrics
    seq_write_ops = []
    seq_read_ops = []
    conc_write_ops = []
    mixed_total_ops = []
    seq_write_latency = []
    seq_read_latency = []
    conc_write_latency = []
    
    for nodes in node_counts:
        data = results[nodes]
        
        # Operations per second
        seq_write_ops.append(data['sequential_writes']['operations_per_second'])
        seq_read_ops.append(data['sequential_reads']['operations_per_second'])
        conc_write_ops.append(data['concurrent_writes']['operations_per_second'])
        mixed_total_ops.append(data['mixed_workload']['total_operations_per_second'])
        
        # Latency (average)
        seq_write_latency.append(data['sequential_writes']['average_latency_ms'])
        seq_read_latency.append(data['sequential_reads']['average_latency_ms'])
        conc_write_latency.append(data['concurrent_writes']['average_latency_ms'])
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('etcd Cluster Performance Comparison', fontsize=16, fontweight='bold')
    
    # 1. Operations per Second
    ax1.plot(node_counts, seq_write_ops, 'o-', label='Sequential Writes', linewidth=2, markersize=8)
    ax1.plot(node_counts, seq_read_ops, 's-', label='Sequential Reads', linewidth=2, markersize=8)
    ax1.plot(node_counts, conc_write_ops, '^-', label='Concurrent Writes', linewidth=2, markersize=8)
    ax1.plot(node_counts, mixed_total_ops, 'd-', label='Mixed Workload', linewidth=2, markersize=8)
    ax1.set_xlabel('Number of Nodes')
    ax1.set_ylabel('Operations per Second')
    ax1.set_title('Throughput vs Cluster Size')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(node_counts)
    
    # 2. Latency
    ax2.plot(node_counts, seq_write_latency, 'o-', label='Sequential Writes', linewidth=2, markersize=8)
    ax2.plot(node_counts, seq_read_latency, 's-', label='Sequential Reads', linewidth=2, markersize=8)
    ax2.plot(node_counts, conc_write_latency, '^-', label='Concurrent Writes', linewidth=2, markersize=8)
    ax2.set_xlabel('Number of Nodes')
    ax2.set_ylabel('Average Latency (ms)')
    ax2.set_title('Latency vs Cluster Size')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(node_counts)
    
    # 3. Read vs Write Performance (Mixed Workload)
    mixed_read_ops = []
    mixed_write_ops = []
    for nodes in node_counts:
        data = results[nodes]
        mixed_read_ops.append(data['mixed_workload']['read_ops_per_second'])
        mixed_write_ops.append(data['mixed_workload']['write_ops_per_second'])
    
    x = np.arange(len(node_counts))
    width = 0.35
    
    ax3.bar(x - width/2, mixed_read_ops, width, label='Reads', alpha=0.8)
    ax3.bar(x + width/2, mixed_write_ops, width, label='Writes', alpha=0.8)
    ax3.set_xlabel('Number of Nodes')
    ax3.set_ylabel('Operations per Second')
    ax3.set_title('Mixed Workload: Read vs Write Performance')
    ax3.set_xticks(x)
    ax3.set_xticklabels(node_counts)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Efficiency: Operations per Node
    efficiency_seq_write = [ops/nodes for ops, nodes in zip(seq_write_ops, node_counts)]
    efficiency_seq_read = [ops/nodes for ops, nodes in zip(seq_read_ops, node_counts)]
    efficiency_conc_write = [ops/nodes for ops, nodes in zip(conc_write_ops, node_counts)]
    
    ax4.plot(node_counts, efficiency_seq_write, 'o-', label='Sequential Writes', linewidth=2, markersize=8)
    ax4.plot(node_counts, efficiency_seq_read, 's-', label='Sequential Reads', linewidth=2, markersize=8)
    ax4.plot(node_counts, efficiency_conc_write, '^-', label='Concurrent Writes', linewidth=2, markersize=8)
    ax4.set_xlabel('Number of Nodes')
    ax4.set_ylabel('Operations per Second per Node')
    ax4.set_title('Efficiency: Performance per Node')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_xticks(node_counts)
    
    plt.tight_layout()
    return fig

def create_summary_table(results):
    """Create a summary table of results"""
    if not results:
        return
    
    print("\n" + "="*100)
    print("ETCD CLUSTER PERFORMANCE SUMMARY")
    print("="*100)
    
    print(f"{'Nodes':<6} {'Seq Write':<12} {'Seq Read':<12} {'Conc Write':<12} {'Mixed Total':<12} {'Write Lat.':<12} {'Read Lat.':<12}")
    print(f"{'':6} {'(ops/s)':<12} {'(ops/s)':<12} {'(ops/s)':<12} {'(ops/s)':<12} {'(ms)':<12} {'(ms)':<12}")
    print("-"*100)
    
    for nodes in sorted(results.keys()):
        data = results[nodes]
        print(f"{nodes:<6} "
              f"{data['sequential_writes']['operations_per_second']:<12.1f} "
              f"{data['sequential_reads']['operations_per_second']:<12.1f} "
              f"{data['concurrent_writes']['operations_per_second']:<12.1f} "
              f"{data['mixed_workload']['total_operations_per_second']:<12.1f} "
              f"{data['sequential_writes']['average_latency_ms']:<12.1f} "
              f"{data['sequential_reads']['average_latency_ms']:<12.1f}")
    
    print("-"*100)
    
    # Performance insights
    if len(results) > 1:
        node_counts = sorted(results.keys())
        min_nodes = min(node_counts)
        max_nodes = max(node_counts)
        
        min_data = results[min_nodes]
        max_data = results[max_nodes]
        
        print("\nPERFORMANCE INSIGHTS:")
        print("-"*50)
        
        # Throughput scaling
        seq_write_scaling = max_data['sequential_writes']['operations_per_second'] / min_data['sequential_writes']['operations_per_second']
        conc_write_scaling = max_data['concurrent_writes']['operations_per_second'] / min_data['concurrent_writes']['operations_per_second']
        
        print(f"Sequential Write Scaling ({min_nodes} → {max_nodes} nodes): {seq_write_scaling:.2f}x")
        print(f"Concurrent Write Scaling ({min_nodes} → {max_nodes} nodes): {conc_write_scaling:.2f}x")
        
        # Latency changes
        seq_write_lat_change = (max_data['sequential_writes']['average_latency_ms'] - min_data['sequential_writes']['average_latency_ms'])
        print(f"Sequential Write Latency Change: {seq_write_lat_change:+.1f}ms")
        
        # Efficiency
        min_efficiency = min_data['concurrent_writes']['operations_per_second'] / min_nodes
        max_efficiency = max_data['concurrent_writes']['operations_per_second'] / max_nodes
        print(f"Efficiency (Concurrent Writes per Node): {min_nodes}n={min_efficiency:.1f} ops/s/node, {max_nodes}n={max_efficiency:.1f} ops/s/node")

def main():
    parser = argparse.ArgumentParser(description='Plot etcd benchmark results')
    parser.add_argument('--pattern', '-p', default='results-*nodes*.json',
                       help='File pattern for result files (default: results-*nodes*.json)')
    parser.add_argument('--output', '-o', default='benchmark_results.png',
                       help='Output file for plot (default: benchmark_results.png)')
    parser.add_argument('--show', '-s', action='store_true',
                       help='Show plot interactively')
    parser.add_argument('--table-only', '-t', action='store_true',
                       help='Show only summary table, no plots')
    
    args = parser.parse_args()
    
    # Load results
    results = load_results(args.pattern)
    
    if not results:
        print("No benchmark results found!")
        print("Make sure you have run benchmarks with files like 'results-3nodes.json'")
        return
    
    # Show summary table
    create_summary_table(results)
    
    if not args.table_only:
        try:
            import matplotlib.pyplot as plt
            
            # Create plots
            fig = create_performance_plots(results)
            
            if fig:
                # Save plot
                fig.savefig(args.output, dpi=300, bbox_inches='tight')
                print(f"\nPlot saved to: {args.output}")
                
                # Show plot if requested
                if args.show:
                    plt.show()
                
                plt.close()
            
        except ImportError:
            print("\nMatplotlib not installed. Install with:")
            print("pip install matplotlib")
            print("\nShowing table only.")

if __name__ == '__main__':
    main()
