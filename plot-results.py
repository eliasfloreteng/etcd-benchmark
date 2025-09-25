#!/usr/bin/env python3
"""
Simple plotting script for etcd cluster benchmark results

Reads benchmark JSON files and creates plots showing:
- Throughput vs Number of Nodes
- Latency vs Number of Nodes

Usage:
    python3 plot-results.py                    # Auto-detect *-nodes.json files
    python3 plot-results.py *.json            # Use specific files
    python3 plot-results.py 1-nodes.json 3-nodes.json 5-nodes.json
"""

import argparse
import glob
import json
import matplotlib.pyplot as plt
import os
import re
import sys


def load_benchmark_data(file_patterns):
    """Load benchmark JSON files from specified patterns and extract key metrics"""
    data = {}

    # Expand file patterns and get all matching files
    files = []
    for pattern in file_patterns:
        if "*" in pattern or "?" in pattern:
            # Use glob for patterns
            matched_files = glob.glob(pattern)
            files.extend(matched_files)
        else:
            # Direct file path
            files.append(pattern)

    # Remove duplicates and sort
    files = sorted(list(set(files)))

    if not files:
        print("❌ No files found matching the specified patterns")
        return data

    print(f"📁 Found {len(files)} files to process")

    for filename in files:
        if not os.path.exists(filename):
            print(f"⚠ File not found: {filename}")
            continue

        try:
            with open(filename, "r") as f:
                result = json.load(f)

            # Determine number of nodes from config.endpoints
            if "config" in result and "endpoints" in result["config"]:
                num_nodes = len(result["config"]["endpoints"])
            else:
                # Fallback: try to extract from filename pattern
                match = re.search(r"(\d+)-?nodes?", filename)
                if match:
                    num_nodes = int(match.group(1))
                else:
                    print(f"⚠ Cannot determine node count for {filename}, skipping")
                    continue

            data[num_nodes] = {
                "throughput": result["throughput_ops_per_sec"],
                "avg_latency": result["avg_latency_ms"],
                "p95_latency": result["p95_latency_ms"],
                "p99_latency": result["p99_latency_ms"],
                "read_throughput": result["read_throughput"],
                "write_throughput": result["write_throughput"],
                "total_operations": result["total_operations"],
                "duration": result["duration_seconds"],
                "filename": filename,
            }
            print(
                f"✓ Loaded {filename}: {num_nodes} nodes, {result['throughput_ops_per_sec']:.1f} ops/sec"
            )
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")

    return data


def create_plots(data, output_file="etcd-performance-analysis.png", show_plot=True):
    """Create throughput and latency plots"""
    if not data:
        print("❌ No data to plot")
        return

    # Extract data for plotting
    nodes = sorted(data.keys())
    throughputs = [data[n]["throughput"] for n in nodes]
    avg_latencies = [data[n]["avg_latency"] for n in nodes]
    p95_latencies = [data[n]["p95_latency"] for n in nodes]
    p99_latencies = [data[n]["p99_latency"] for n in nodes]
    read_throughputs = [data[n]["read_throughput"] for n in nodes]
    write_throughputs = [data[n]["write_throughput"] for n in nodes]

    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("ETCD Cluster Performance Analysis", fontsize=16, fontweight="bold")

    # Plot 1: Overall Throughput vs Nodes
    ax1.plot(
        nodes, throughputs, "bo-", linewidth=2, markersize=8, label="Total Throughput"
    )
    ax1.plot(
        nodes,
        read_throughputs,
        "go-",
        linewidth=1,
        markersize=6,
        label="Read Throughput",
    )
    ax1.plot(
        nodes,
        write_throughputs,
        "ro-",
        linewidth=1,
        markersize=6,
        label="Write Throughput",
    )
    ax1.set_xlabel("Number of Nodes")
    ax1.set_ylabel("Throughput (ops/sec)")
    ax1.set_title("Throughput vs Number of Nodes")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_xticks(nodes)

    # Add throughput annotations
    for i, (n, t) in enumerate(zip(nodes, throughputs)):
        ax1.annotate(
            f"{t:.0f}",
            (n, t),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
        )

    # Plot 2: Latency Percentiles vs Nodes
    ax2.plot(nodes, avg_latencies, "b-o", linewidth=2, markersize=6, label="Average")
    ax2.plot(nodes, p95_latencies, "r-s", linewidth=2, markersize=6, label="P95")
    ax2.plot(nodes, p99_latencies, "g-^", linewidth=2, markersize=6, label="P99")
    ax2.set_xlabel("Number of Nodes")
    ax2.set_ylabel("Latency (ms)")
    ax2.set_title("Latency vs Number of Nodes")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_xticks(nodes)

    # Plot 3: Throughput Scaling Efficiency
    baseline_throughput = throughputs[0]  # 1-node throughput
    scaling_efficiency = [
        (t / baseline_throughput) / n * 100 for n, t in zip(nodes, throughputs)
    ]

    ax3.plot(nodes, scaling_efficiency, "mo-", linewidth=2, markersize=8)
    ax3.axhline(y=100, color="gray", linestyle="--", alpha=0.7, label="Perfect Scaling")
    ax3.set_xlabel("Number of Nodes")
    ax3.set_ylabel("Scaling Efficiency (%)")
    ax3.set_title("Throughput Scaling Efficiency")
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    ax3.set_xticks(nodes)

    # Add efficiency annotations
    for i, (n, eff) in enumerate(zip(nodes, scaling_efficiency)):
        ax3.annotate(
            f"{eff:.1f}%",
            (n, eff),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
        )

    # Plot 4: Operations per Node
    ops_per_node = [data[n]["total_operations"] / n for n in nodes]

    ax4.bar(nodes, ops_per_node, alpha=0.7, color="skyblue", edgecolor="navy")
    ax4.set_xlabel("Number of Nodes")
    ax4.set_ylabel("Operations per Node")
    ax4.set_title("Load Distribution (Total Ops / Number of Nodes)")
    ax4.grid(True, alpha=0.3, axis="y")
    ax4.set_xticks(nodes)

    # Add value annotations on bars
    for i, (n, ops) in enumerate(zip(nodes, ops_per_node)):
        ax4.annotate(
            f"{ops:.0f}",
            (n, ops),
            textcoords="offset points",
            xytext=(0, 5),
            ha="center",
            fontsize=9,
        )

    plt.tight_layout()

    # Save the plot
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"📊 Plot saved as '{output_file}'")

    # Show the plot if requested
    if show_plot:
        plt.show()
    else:
        plt.close()


def print_summary(data):
    """Print a summary of the results"""
    if not data:
        return

    nodes = sorted(data.keys())

    print("\n" + "=" * 60)
    print("ETCD CLUSTER PERFORMANCE SUMMARY")
    print("=" * 60)

    print(
        f"{'Nodes':<6} {'Throughput':<12} {'Avg Latency':<12} {'P95 Latency':<12} {'P99 Latency':<12}"
    )
    print("-" * 60)

    for n in nodes:
        d = data[n]
        print(
            f"{n:<6} {d['throughput']:<12.1f} {d['avg_latency']:<12.2f} {d['p95_latency']:<12.2f} {d['p99_latency']:<12.2f}"
        )

    # Calculate improvements
    if len(nodes) > 1:
        baseline = data[1]
        best_node = max(nodes)
        best = data[best_node]

        throughput_improvement = (best["throughput"] / baseline["throughput"] - 1) * 100
        latency_change = (best["avg_latency"] / baseline["avg_latency"] - 1) * 100

        print(f"\n📈 Performance Gains (1 node vs {best_node} nodes):")
        print(f"   Throughput: {throughput_improvement:+.1f}%")
        print(f"   Avg Latency: {latency_change:+.1f}%")

        # Find optimal node count based on throughput per node
        throughput_per_node = {n: data[n]["throughput"] / n for n in nodes}
        optimal_nodes = max(throughput_per_node, key=throughput_per_node.get)
        print(f"   Optimal node count (efficiency): {optimal_nodes} nodes")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="ETCD Cluster Performance Plotter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 plot-results.py                           # Auto-detect *-nodes.json files
  python3 plot-results.py *.json                   # Use glob patterns
  python3 plot-results.py result1.json result2.json # Specific files
  python3 plot-results.py benchmark-*.json         # Pattern matching
        """,
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="JSON files to analyze (supports glob patterns). If not specified, auto-detects *-nodes.json files.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="etcd-performance-analysis.png",
        help="Output filename for the plot (default: etcd-performance-analysis.png)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Skip displaying the plot (only save to file)",
    )

    args = parser.parse_args()

    print("📊 ETCD Cluster Performance Plotter")
    print("==================================")

    # Determine files to process
    if args.files:
        file_patterns = args.files
        print(f"\n📂 Using specified files/patterns: {file_patterns}")
    else:
        # Auto-detect pattern
        file_patterns = ["*-nodes.json"]
        print(f"\n📂 Auto-detecting files with pattern: {file_patterns}")

    # Load benchmark data
    data = load_benchmark_data(file_patterns)

    if not data:
        print("❌ No benchmark data found. Please run benchmarks first.")
        print(
            "Example: python3 benchmark-etcd-cluster.py --duration 30 --clients 10 --output 1-nodes.json"
        )
        return 1

    # Print summary
    print_summary(data)

    # Create plots
    print("\n🎨 Creating plots...")
    create_plots(data, output_file=args.output, show_plot=not args.no_display)

    print("\n✅ Analysis complete!")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
