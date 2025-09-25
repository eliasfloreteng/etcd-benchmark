#!/usr/bin/env python3
"""
ETCD Cluster Benchmark Tool

A comprehensive benchmarking tool for etcd clusters that measures:
- Read/Write throughput
- Latency statistics
- Concurrent client performance
- Load distribution across nodes

Usage: python3 benchmark-etcd-cluster.py [options]
"""

import argparse
import asyncio
import concurrent.futures
import etcd3
import json
import random
import statistics
import string
import sys
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Tuple


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark parameters"""

    endpoints: List[str]
    num_clients: int = 10
    duration: int = 30
    write_ratio: float = 0.3
    key_size: int = 64
    value_size: int = 1024
    key_prefix: str = "benchmark"
    warmup_time: int = 5
    report_interval: int = 5


@dataclass
class OperationResult:
    """Result of a single operation"""

    operation: str  # 'read' or 'write'
    success: bool
    latency_ms: float
    timestamp: float
    endpoint: str
    error: str = ""


@dataclass
class BenchmarkResults:
    """Aggregated benchmark results"""

    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_reads: int = 0
    total_writes: int = 0
    successful_reads: int = 0
    successful_writes: int = 0
    duration_seconds: float = 0
    throughput_ops_per_sec: float = 0
    read_throughput: float = 0
    write_throughput: float = 0
    avg_latency_ms: float = 0
    min_latency_ms: float = 0
    max_latency_ms: float = 0
    p50_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    read_latency_stats: Dict[str, float] = None
    write_latency_stats: Dict[str, float] = None
    endpoint_distribution: Dict[str, int] = None
    errors: List[str] = None


class EtcdBenchmarkClient:
    """Individual benchmark client for etcd operations"""

    def __init__(self, client_id: int, config: BenchmarkConfig):
        self.client_id = client_id
        self.config = config
        self.results: List[OperationResult] = []
        self.running = False
        self.etcd_clients = {}

        # Initialize etcd clients for each endpoint
        for endpoint in config.endpoints:
            host, port = endpoint.replace("http://", "").split(":")
            try:
                client = etcd3.client(host=host, port=int(port))
                self.etcd_clients[endpoint] = client
            except Exception as e:
                print(f"Failed to connect to {endpoint}: {e}")

    def generate_random_key(self) -> str:
        """Generate a random key with the configured prefix"""
        suffix = "".join(
            random.choices(
                string.ascii_letters + string.digits,
                k=self.config.key_size - len(self.config.key_prefix) - 1,
            )
        )
        return f"{self.config.key_prefix}_{suffix}"

    def generate_random_value(self) -> str:
        """Generate a random value of configured size"""
        return "".join(
            random.choices(
                string.ascii_letters + string.digits + " ", k=self.config.value_size
            )
        )

    def perform_operation(self) -> OperationResult:
        """Perform a single read or write operation"""
        # Choose operation type based on write ratio
        is_write = random.random() < self.config.write_ratio
        operation = "write" if is_write else "read"

        # Choose random endpoint
        endpoint = random.choice(self.config.endpoints)
        client = self.etcd_clients.get(endpoint)

        if not client:
            return OperationResult(
                operation=operation,
                success=False,
                latency_ms=0,
                timestamp=time.time(),
                endpoint=endpoint,
                error="No client available for endpoint",
            )

        start_time = time.perf_counter()

        try:
            if is_write:
                key = self.generate_random_key()
                value = self.generate_random_value()
                client.put(key, value)
            else:
                # For reads, try to read existing keys or generate new ones
                key = self.generate_random_key()
                result = client.get(key)
                # We don't care if the key exists or not for benchmark purposes

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return OperationResult(
                operation=operation,
                success=True,
                latency_ms=latency_ms,
                timestamp=time.time(),
                endpoint=endpoint,
            )

        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return OperationResult(
                operation=operation,
                success=False,
                latency_ms=latency_ms,
                timestamp=time.time(),
                endpoint=endpoint,
                error=str(e),
            )

    def run(self, duration: int):
        """Run benchmark operations for specified duration"""
        self.running = True
        start_time = time.time()

        while self.running and (time.time() - start_time) < duration:
            result = self.perform_operation()
            self.results.append(result)

            # Small delay to prevent overwhelming the cluster
            time.sleep(0.001)  # 1ms delay

    def stop(self):
        """Stop the benchmark client"""
        self.running = False


class EtcdBenchmark:
    """Main benchmark orchestrator"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.clients: List[EtcdBenchmarkClient] = []
        self.results = BenchmarkResults()

    def detect_cluster_nodes(self) -> List[str]:
        """Detect available etcd nodes if not specified"""
        endpoints = []
        base_port = 2379

        for i in range(1, 11):  # Check ports 2379-2388
            port = base_port + i - 1
            endpoint = f"http://localhost:{port}"
            try:
                client = etcd3.client(host="localhost", port=port)
                # Test connection with a simple operation
                client.status()
                endpoints.append(endpoint)
                print(f"✓ Detected etcd node at {endpoint}")
            except Exception:
                continue  # Node not available

        return endpoints

    def prepare_benchmark(self):
        """Prepare the benchmark environment"""
        print("Preparing benchmark environment...")

        # Auto-detect cluster nodes if not specified
        if not self.config.endpoints:
            detected_endpoints = self.detect_cluster_nodes()
            if not detected_endpoints:
                raise RuntimeError(
                    "No etcd nodes detected. Please start the cluster first."
                )
            self.config.endpoints = detected_endpoints

        print(f"Using endpoints: {self.config.endpoints}")
        print(f"Benchmark configuration:")
        print(f"  - Clients: {self.config.num_clients}")
        print(f"  - Duration: {self.config.duration}s")
        print(f"  - Write ratio: {self.config.write_ratio:.1%}")
        print(f"  - Key size: {self.config.key_size} bytes")
        print(f"  - Value size: {self.config.value_size} bytes")

        # Create benchmark clients
        self.clients = [
            EtcdBenchmarkClient(i, self.config) for i in range(self.config.num_clients)
        ]

        # Warmup phase
        if self.config.warmup_time > 0:
            print(f"\nWarming up for {self.config.warmup_time}s...")
            self.run_warmup()

    def run_warmup(self):
        """Run warmup operations to prepare the cluster"""
        warmup_client = EtcdBenchmarkClient(0, self.config)

        for _ in range(100):  # Perform 100 warmup operations
            warmup_client.perform_operation()
            time.sleep(0.01)

    def run_benchmark(self):
        """Execute the main benchmark"""
        print(f"\nStarting benchmark with {self.config.num_clients} clients...")

        # Start all clients in separate threads
        threads = []
        start_time = time.time()

        for client in self.clients:
            thread = threading.Thread(target=client.run, args=(self.config.duration,))
            thread.start()
            threads.append(thread)

        # Progress reporting
        self.report_progress(start_time)

        # Wait for all clients to finish
        for thread in threads:
            thread.join()

        end_time = time.time()
        actual_duration = end_time - start_time

        print(f"\nBenchmark completed in {actual_duration:.2f}s")
        return actual_duration

    def report_progress(self, start_time: float):
        """Report progress during benchmark execution"""
        last_report = 0

        while True:
            elapsed = time.time() - start_time

            if elapsed >= self.config.duration:
                break

            if elapsed - last_report >= self.config.report_interval:
                # Calculate current stats
                total_ops = sum(len(client.results) for client in self.clients)
                ops_per_sec = total_ops / elapsed if elapsed > 0 else 0

                print(
                    f"Progress: {elapsed:.0f}s / {self.config.duration}s | "
                    f"Operations: {total_ops} | "
                    f"Throughput: {ops_per_sec:.1f} ops/sec"
                )

                last_report = elapsed

            time.sleep(1)

    def analyze_results(self, actual_duration: float) -> BenchmarkResults:
        """Analyze and aggregate benchmark results"""
        print("\nAnalyzing results...")

        all_results: List[OperationResult] = []
        for client in self.clients:
            all_results.extend(client.results)

        if not all_results:
            raise RuntimeError("No results to analyze")

        # Basic statistics
        total_ops = len(all_results)
        successful_ops = sum(1 for r in all_results if r.success)
        failed_ops = total_ops - successful_ops

        reads = [r for r in all_results if r.operation == "read"]
        writes = [r for r in all_results if r.operation == "write"]
        successful_reads = [r for r in reads if r.success]
        successful_writes = [r for r in writes if r.success]

        # Latency statistics
        successful_latencies = [r.latency_ms for r in all_results if r.success]
        read_latencies = [r.latency_ms for r in successful_reads]
        write_latencies = [r.latency_ms for r in successful_writes]

        # Endpoint distribution
        endpoint_counts = defaultdict(int)
        for result in all_results:
            endpoint_counts[result.endpoint] += 1

        # Error collection
        errors = [r.error for r in all_results if not r.success and r.error]

        # Calculate statistics
        def calc_percentiles(data):
            if not data:
                return 0, 0, 0, 0, 0, 0
            return (
                statistics.mean(data),
                min(data),
                max(data),
                statistics.median(data),
                self.percentile(data, 0.95),
                self.percentile(data, 0.99),
            )

        avg_lat, min_lat, max_lat, p50_lat, p95_lat, p99_lat = calc_percentiles(
            successful_latencies
        )
        read_stats = calc_percentiles(read_latencies)
        write_stats = calc_percentiles(write_latencies)

        # Create results object
        self.results = BenchmarkResults(
            total_operations=total_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            total_reads=len(reads),
            total_writes=len(writes),
            successful_reads=len(successful_reads),
            successful_writes=len(successful_writes),
            duration_seconds=actual_duration,
            throughput_ops_per_sec=successful_ops / actual_duration,
            read_throughput=len(successful_reads) / actual_duration,
            write_throughput=len(successful_writes) / actual_duration,
            avg_latency_ms=avg_lat,
            min_latency_ms=min_lat,
            max_latency_ms=max_lat,
            p50_latency_ms=p50_lat,
            p95_latency_ms=p95_lat,
            p99_latency_ms=p99_lat,
            read_latency_stats={
                "avg": read_stats[0],
                "min": read_stats[1],
                "max": read_stats[2],
                "p50": read_stats[3],
                "p95": read_stats[4],
                "p99": read_stats[5],
            },
            write_latency_stats={
                "avg": write_stats[0],
                "min": write_stats[1],
                "max": write_stats[2],
                "p50": write_stats[3],
                "p95": write_stats[4],
                "p99": write_stats[5],
            },
            endpoint_distribution=dict(endpoint_counts),
            errors=list(set(errors)),  # Unique errors
        )

        return self.results

    @staticmethod
    def percentile(data, p):
        """Calculate percentile of data"""
        if not data:
            return 0
        return statistics.quantiles(data, n=100)[int(p * 100) - 1]

    def print_results(self):
        """Print formatted benchmark results"""
        r = self.results

        print("\n" + "=" * 60)
        print("ETCD CLUSTER BENCHMARK RESULTS")
        print("=" * 60)

        print(f"\n📊 OVERVIEW")
        print(f"Duration: {r.duration_seconds:.2f}s")
        print(f"Total Operations: {r.total_operations:,}")
        print(
            f"Successful Operations: {r.successful_operations:,} ({r.successful_operations / r.total_operations:.1%})"
        )
        print(f"Failed Operations: {r.failed_operations:,}")

        print(f"\n🚀 THROUGHPUT")
        print(f"Overall: {r.throughput_ops_per_sec:.1f} ops/sec")
        print(f"Read Throughput: {r.read_throughput:.1f} reads/sec")
        print(f"Write Throughput: {r.write_throughput:.1f} writes/sec")

        print(f"\n⏱️  LATENCY (ms)")
        print(f"Average: {r.avg_latency_ms:.2f}ms")
        print(f"Min: {r.min_latency_ms:.2f}ms")
        print(f"Max: {r.max_latency_ms:.2f}ms")
        print(f"P50: {r.p50_latency_ms:.2f}ms")
        print(f"P95: {r.p95_latency_ms:.2f}ms")
        print(f"P99: {r.p99_latency_ms:.2f}ms")

        if r.read_latency_stats and r.read_latency_stats["avg"] > 0:
            print(f"\n📖 READ LATENCY (ms)")
            print(f"Average: {r.read_latency_stats['avg']:.2f}ms")
            print(f"P50: {r.read_latency_stats['p50']:.2f}ms")
            print(f"P95: {r.read_latency_stats['p95']:.2f}ms")
            print(f"P99: {r.read_latency_stats['p99']:.2f}ms")

        if r.write_latency_stats and r.write_latency_stats["avg"] > 0:
            print(f"\n✍️  WRITE LATENCY (ms)")
            print(f"Average: {r.write_latency_stats['avg']:.2f}ms")
            print(f"P50: {r.write_latency_stats['p50']:.2f}ms")
            print(f"P95: {r.write_latency_stats['p95']:.2f}ms")
            print(f"P99: {r.write_latency_stats['p99']:.2f}ms")

        print(f"\n🌐 ENDPOINT DISTRIBUTION")
        for endpoint, count in r.endpoint_distribution.items():
            percentage = (count / r.total_operations) * 100
            print(f"{endpoint}: {count:,} operations ({percentage:.1f}%)")

        if r.errors:
            print(f"\n❌ ERRORS ({len(r.errors)} unique)")
            for i, error in enumerate(r.errors[:5], 1):  # Show first 5 errors
                print(f"{i}. {error}")
            if len(r.errors) > 5:
                print(f"... and {len(r.errors) - 5} more")

        print(f"\n" + "=" * 60)

    def save_results_json(self, filename: str):
        """Save results to JSON file"""
        results_dict = asdict(self.results)
        results_dict["timestamp"] = datetime.now().isoformat()
        results_dict["config"] = asdict(self.config)

        with open(filename, "w") as f:
            json.dump(results_dict, f, indent=2)

        print(f"Results saved to {filename}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="ETCD Cluster Benchmark Tool")

    parser.add_argument(
        "--endpoints",
        "-e",
        nargs="+",
        help="ETCD endpoints (e.g., http://localhost:2379)",
    )
    parser.add_argument(
        "--clients",
        "-c",
        type=int,
        default=10,
        help="Number of concurrent clients (default: 10)",
    )
    parser.add_argument(
        "--duration",
        "-d",
        type=int,
        default=30,
        help="Benchmark duration in seconds (default: 30)",
    )
    parser.add_argument(
        "--write-ratio",
        "-w",
        type=float,
        default=0.3,
        help="Ratio of write operations (0.0-1.0, default: 0.3)",
    )
    parser.add_argument(
        "--key-size", type=int, default=64, help="Key size in bytes (default: 64)"
    )
    parser.add_argument(
        "--value-size",
        type=int,
        default=1024,
        help="Value size in bytes (default: 1024)",
    )
    parser.add_argument(
        "--key-prefix",
        default="benchmark",
        help="Key prefix for benchmark (default: benchmark)",
    )
    parser.add_argument(
        "--warmup-time", type=int, default=5, help="Warmup time in seconds (default: 5)"
    )
    parser.add_argument("--output", "-o", help="Output JSON file for results")
    parser.add_argument(
        "--no-auto-detect", action="store_true", help="Disable automatic node detection"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.write_ratio < 0 or args.write_ratio > 1:
        print("Error: Write ratio must be between 0.0 and 1.0")
        return 1

    # Create configuration
    config = BenchmarkConfig(
        endpoints=args.endpoints or [],
        num_clients=args.clients,
        duration=args.duration,
        write_ratio=args.write_ratio,
        key_size=args.key_size,
        value_size=args.value_size,
        key_prefix=args.key_prefix,
        warmup_time=args.warmup_time,
    )

    try:
        # Create and run benchmark
        benchmark = EtcdBenchmark(config)
        benchmark.prepare_benchmark()

        actual_duration = benchmark.run_benchmark()
        benchmark.analyze_results(actual_duration)
        benchmark.print_results()

        # Save results if requested
        if args.output:
            benchmark.save_results_json(args.output)

        return 0

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        return 1
    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
