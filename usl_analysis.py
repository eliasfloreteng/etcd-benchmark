#!/usr/bin/env python3
"""
Universal Scalability Law Analysis for etcd Benchmark Results

The Universal Scalability Law (USL) models how systems scale with the number of processors/nodes.
It helps identify contention and coherency delays that limit scalability.

USL Formula: C(N) = N / (1 + α(N-1) + βN(N-1))
Where:
- C(N) = Relative capacity (throughput) at N nodes
- N = Number of nodes
- α = Contention coefficient (serialization)
- β = Coherency coefficient (crosstalk/coordination overhead)
"""

import json
import glob
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import argparse
import re
from pathlib import Path

def extract_node_count(filename):
    """Extract node count from filename"""
    match = re.search(r'results-(\d+)nodes?\.json', filename)
    if match:
        return int(match.group(1))
    return None

def load_benchmark_results(pattern="results-*nodes*.json"):
    """Load benchmark results and extract throughput data"""
    results = {}
    
    files = glob.glob(pattern)
    if not files:
        print(f"No files found matching pattern: {pattern}")
        return results
    
    for file in files:
        node_count = extract_node_count(file)
        if node_count is None:
            continue
            
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                results[node_count] = data
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    return results

def usl_function(N, alpha, beta):
    """Universal Scalability Law function"""
    return N / (1 + alpha * (N - 1) + beta * N * (N - 1))

def fit_usl_model(nodes, throughput):
    """Fit USL model to throughput data"""
    # Normalize throughput to single-node baseline
    normalized_throughput = np.array(throughput) / throughput[0]
    nodes_array = np.array(nodes)
    
    try:
        # Fit the USL model
        popt, pcov = curve_fit(usl_function, nodes_array, normalized_throughput, 
                              bounds=([0, 0], [1, 1]), maxfev=10000)
        alpha, beta = popt
        
        # Calculate confidence intervals
        param_errors = np.sqrt(np.diag(pcov))
        alpha_err, beta_err = param_errors
        
        # Calculate R-squared
        y_pred = usl_function(nodes_array, alpha, beta)
        ss_res = np.sum((normalized_throughput - y_pred) ** 2)
        ss_tot = np.sum((normalized_throughput - np.mean(normalized_throughput)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)
        
        return alpha, beta, alpha_err, beta_err, r_squared, normalized_throughput
    except Exception as e:
        print(f"USL fitting failed: {e}")
        return None, None, None, None, None, None

def calculate_usl_predictions(alpha, beta, max_nodes=20):
    """Calculate USL predictions for visualization"""
    nodes = np.arange(1, max_nodes + 1)
    capacity = usl_function(nodes, alpha, beta)
    throughput = capacity  # Relative to single node
    
    # Find optimal point (maximum capacity)
    optimal_idx = np.argmax(capacity)
    optimal_nodes = nodes[optimal_idx]
    optimal_capacity = capacity[optimal_idx]
    
    return nodes, capacity, throughput, optimal_nodes, optimal_capacity

def interpret_usl_coefficients(alpha, beta, alpha_err, beta_err):
    """Interpret USL coefficients and provide insights"""
    interpretation = []
    
    interpretation.append("=== UNIVERSAL SCALABILITY LAW ANALYSIS ===\n")
    
    # Contention coefficient (α)
    interpretation.append(f"Contention Coefficient (α): {alpha:.4f} ± {alpha_err:.4f}")
    if alpha < 0.1:
        interpretation.append("  → Low contention: Good serialization characteristics")
    elif alpha < 0.3:
        interpretation.append("  → Moderate contention: Some serialization bottlenecks")
    else:
        interpretation.append("  → High contention: Significant serialization bottlenecks")
    
    interpretation.append("")
    
    # Coherency coefficient (β)
    interpretation.append(f"Coherency Coefficient (β): {beta:.4f} ± {beta_err:.4f}")
    if beta < 0.01:
        interpretation.append("  → Low coherency delay: Minimal coordination overhead")
    elif beta < 0.05:
        interpretation.append("  → Moderate coherency delay: Some coordination overhead")
    else:
        interpretation.append("  → High coherency delay: Significant coordination overhead")
    
    interpretation.append("")
    
    # System characteristics
    if beta > alpha:
        interpretation.append("β > α: System is coherency-limited (coordination overhead dominates)")
        interpretation.append("This is typical for distributed consensus systems like etcd")
    else:
        interpretation.append("α > β: System is contention-limited (serialization dominates)")
    
    interpretation.append("")
    
    # Scalability assessment
    total_overhead = alpha + beta
    if total_overhead < 0.1:
        interpretation.append("Overall Assessment: Excellent scalability")
    elif total_overhead < 0.3:
        interpretation.append("Overall Assessment: Good scalability with some limitations")
    elif total_overhead < 0.5:
        interpretation.append("Overall Assessment: Limited scalability")
    else:
        interpretation.append("Overall Assessment: Poor scalability")
    
    return "\n".join(interpretation)

def create_usl_analysis_plots(results):
    """Create comprehensive USL analysis plots"""
    if not results:
        print("No results to analyze")
        return None
    
    # Extract data for different workloads
    workloads = {
        'Sequential Writes': 'sequential_writes',
        'Sequential Reads': 'sequential_reads', 
        'Concurrent Writes': 'concurrent_writes',
        'Mixed Workload': 'mixed_workload'
    }
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Universal Scalability Law Analysis - etcd Performance', fontsize=16, fontweight='bold')
    
    analyses = {}
    
    for idx, (workload_name, workload_key) in enumerate(workloads.items()):
        ax = axes[idx // 2, idx % 2]
        
        # Extract data
        nodes = sorted(results.keys())
        if workload_key == 'mixed_workload':
            throughput = [results[n][workload_key]['total_operations_per_second'] for n in nodes]
        else:
            throughput = [results[n][workload_key]['operations_per_second'] for n in nodes]
        
        # Fit USL model
        alpha, beta, alpha_err, beta_err, r_squared, normalized_throughput = fit_usl_model(nodes, throughput)
        
        if alpha is not None:
            analyses[workload_name] = {
                'alpha': alpha, 'beta': beta,
                'alpha_err': alpha_err, 'beta_err': beta_err,
                'r_squared': r_squared,
                'nodes': nodes,
                'throughput': throughput,
                'normalized_throughput': normalized_throughput
            }
            
            # Generate predictions
            pred_nodes, pred_capacity, pred_throughput, optimal_nodes, optimal_capacity = calculate_usl_predictions(alpha, beta)
            
            # Plot actual data
            ax.scatter(nodes, normalized_throughput, color='red', s=100, zorder=5, label='Measured', alpha=0.8)
            
            # Plot USL model
            ax.plot(pred_nodes, pred_capacity, 'b-', linewidth=2, label=f'USL Model (R²={r_squared:.3f})')
            
            # Plot optimal point
            ax.axvline(optimal_nodes, color='green', linestyle='--', alpha=0.7, label=f'Optimal: {optimal_nodes:.1f} nodes')
            
            # Linear scaling reference
            linear_scaling = np.array(pred_nodes) / pred_nodes[0]
            ax.plot(pred_nodes, linear_scaling, 'gray', linestyle=':', alpha=0.5, label='Linear Scaling')
            
            ax.set_xlabel('Number of Nodes')
            ax.set_ylabel('Relative Capacity')
            ax.set_title(f'{workload_name}\nα={alpha:.3f}, β={beta:.3f}')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.set_xlim(1, max(20, max(nodes) + 2))
            ax.set_ylim(0, max(2, max(normalized_throughput) * 1.1))
    
    plt.tight_layout()
    return fig, analyses

def generate_usl_report(analyses):
    """Generate comprehensive USL analysis report"""
    report = []
    
    report.append("="*80)
    report.append("UNIVERSAL SCALABILITY LAW ANALYSIS REPORT")
    report.append("="*80)
    report.append("")
    
    # Overall summary
    report.append("EXECUTIVE SUMMARY")
    report.append("-" * 50)
    
    avg_alpha = np.mean([a['alpha'] for a in analyses.values()])
    avg_beta = np.mean([a['beta'] for a in analyses.values()])
    
    report.append(f"Average Contention Coefficient (α): {avg_alpha:.4f}")
    report.append(f"Average Coherency Coefficient (β): {avg_beta:.4f}")
    report.append("")
    
    if avg_beta > avg_alpha:
        report.append("SYSTEM CHARACTERISTIC: Coherency-Limited")
        report.append("The system is primarily limited by coordination overhead between nodes.")
        report.append("This is typical for distributed consensus systems like etcd that require")
        report.append("extensive communication between nodes for consistency guarantees.")
    else:
        report.append("SYSTEM CHARACTERISTIC: Contention-Limited") 
        report.append("The system is primarily limited by serialization bottlenecks.")
    
    report.append("")
    
    # Detailed analysis for each workload
    for workload_name, analysis in analyses.items():
        report.append(f"{workload_name.upper()} ANALYSIS")
        report.append("-" * 50)
        
        alpha, beta = analysis['alpha'], analysis['beta']
        alpha_err, beta_err = analysis['alpha_err'], analysis['beta_err']
        r_squared = analysis['r_squared']
        
        report.append(f"Model Fit Quality (R²): {r_squared:.4f}")
        if r_squared > 0.9:
            report.append("  → Excellent fit: Model explains data very well")
        elif r_squared > 0.7:
            report.append("  → Good fit: Model explains data reasonably well")
        else:
            report.append("  → Poor fit: Model may not capture system behavior")
        
        report.append("")
        report.append(f"Contention (α): {alpha:.4f} ± {alpha_err:.4f}")
        report.append(f"Coherency (β): {beta:.4f} ± {beta_err:.4f}")
        report.append("")
        
        # Calculate key metrics
        nodes = np.array(analysis['nodes'])
        pred_nodes, pred_capacity, _, optimal_nodes, optimal_capacity = calculate_usl_predictions(alpha, beta)
        
        report.append(f"Predicted Optimal Cluster Size: {optimal_nodes:.1f} nodes")
        report.append(f"Maximum Relative Capacity: {optimal_capacity:.2f}x")
        
        # Efficiency at measured points
        actual_nodes = analysis['nodes']
        actual_normalized = analysis['normalized_throughput']
        
        report.append("")
        report.append("Efficiency Analysis:")
        for i, (n, capacity) in enumerate(zip(actual_nodes, actual_normalized)):
            efficiency = capacity / n * 100
            report.append(f"  {n} nodes: {efficiency:.1f}% efficiency ({capacity:.2f}x capacity)")
        
        report.append("")
        
        # Scalability recommendations
        if optimal_nodes <= max(actual_nodes):
            report.append(f"⚠️  RECOMMENDATION: Optimal cluster size ({optimal_nodes:.0f} nodes) reached or exceeded")
            report.append("   Adding more nodes will decrease performance")
        else:
            report.append(f"📈 RECOMMENDATION: Can scale up to {optimal_nodes:.0f} nodes for optimal performance")
        
        report.append("")
        report.append("")
    
    # etcd-specific insights
    report.append("ETCD-SPECIFIC INSIGHTS")
    report.append("-" * 50)
    report.append("• High coherency coefficient (β) is expected for etcd due to Raft consensus")
    report.append("• Each write requires majority consensus, increasing coordination overhead")
    report.append("• Read performance may be less affected if reads can be served from followers")
    report.append("• Consider read-only replicas for read-heavy workloads")
    report.append("• Cluster sizes of 3-5 nodes typically provide best balance of performance and fault tolerance")
    report.append("")
    
    # Performance optimization recommendations
    report.append("OPTIMIZATION RECOMMENDATIONS")
    report.append("-" * 50)
    report.append("1. Network Optimization:")
    report.append("   • Minimize network latency between nodes")
    report.append("   • Use dedicated network for cluster communication")
    report.append("   • Consider cluster locality (same datacenter/availability zone)")
    report.append("")
    report.append("2. Workload Optimization:")
    report.append("   • Batch small operations when possible")
    report.append("   • Use transactions for related operations")
    report.append("   • Consider read replicas for read-heavy workloads")
    report.append("")
    report.append("3. Configuration Tuning:")
    report.append("   • Adjust heartbeat and election timeouts based on network latency")
    report.append("   • Tune compaction settings for your data patterns")
    report.append("   • Monitor and optimize disk I/O performance")
    
    return "\n".join(report)

def main():
    parser = argparse.ArgumentParser(description='Universal Scalability Law analysis for etcd benchmarks')
    parser.add_argument('--pattern', '-p', default='results-*nodes*.json',
                       help='File pattern for result files')
    parser.add_argument('--output', '-o', default='usl_analysis.png',
                       help='Output file for plots')
    parser.add_argument('--report', '-r', default='usl_report.txt',
                       help='Output file for analysis report')
    parser.add_argument('--show', '-s', action='store_true',
                       help='Show plots interactively')
    
    args = parser.parse_args()
    
    print("Loading benchmark results...")
    results = load_benchmark_results(args.pattern)
    
    if not results:
        print("No benchmark results found!")
        print("Make sure you have run benchmarks with files like 'results-3nodes.json'")
        return
    
    print(f"Loaded results for {len(results)} different cluster sizes")
    
    try:
        import matplotlib.pyplot as plt
        from scipy.optimize import curve_fit
        
        # Create USL analysis plots
        fig, analyses = create_usl_analysis_plots(results)
        
        if fig and analyses:
            # Save plots
            fig.savefig(args.output, dpi=300, bbox_inches='tight')
            print(f"USL analysis plots saved to: {args.output}")
            
            # Generate and save report
            report = generate_usl_report(analyses)
            with open(args.report, 'w') as f:
                f.write(report)
            print(f"USL analysis report saved to: {args.report}")
            
            # Print summary to console
            print("\n" + "="*60)
            print("QUICK USL ANALYSIS SUMMARY")
            print("="*60)
            
            for workload_name, analysis in analyses.items():
                alpha, beta = analysis['alpha'], analysis['beta']
                r_squared = analysis['r_squared']
                
                # Calculate optimal nodes
                pred_nodes, pred_capacity, _, optimal_nodes, optimal_capacity = calculate_usl_predictions(alpha, beta)
                
                print(f"\n{workload_name}:")
                print(f"  Contention (α): {alpha:.4f}")
                print(f"  Coherency (β): {beta:.4f}")
                print(f"  Model Fit (R²): {r_squared:.4f}")
                print(f"  Optimal Nodes: {optimal_nodes:.1f}")
                print(f"  Max Capacity: {optimal_capacity:.2f}x")
                
                if beta > alpha:
                    print(f"  Bottleneck: Coordination overhead (β > α)")
                else:
                    print(f"  Bottleneck: Serialization (α > β)")
            
            print(f"\nFor detailed analysis, see: {args.report}")
            
            # Show plots if requested
            if args.show:
                plt.show()
            
            plt.close()
        
    except ImportError as e:
        print(f"Required packages not installed: {e}")
        print("Install with: pip install matplotlib scipy")

if __name__ == '__main__':
    main()
