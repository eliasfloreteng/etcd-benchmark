#!/usr/bin/env python3
"""
etcd Cluster Performance Benchmark Tool
Measures performance across different cluster sizes for comparison
"""

import argparse
import json
import time
import subprocess
import sys
import statistics
from datetime import datetime
from pathlib import Path
import concurrent.futures
import threading

class EtcdBenchmark:
    def __init__(self, compose_file="docker-compose-generated.yml"):
        self.compose_file = compose_file
        self.results = {}
        
    def run_etcdctl_command(self, command, timeout=30):
        """Run etcdctl command in the first container"""
        full_command = [
            "docker-compose", "-f", self.compose_file,
            "exec", "-T", "etcd-1", "etcdctl"
        ] + command
        
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def check_cluster_health(self):
        """Check if cluster is healthy before benchmarking"""
        success, stdout, stderr = self.run_etcdctl_command(["endpoint", "health"])
        if not success:
            print(f"Cluster health check failed: {stderr}")
            return False
        
        # Check member list
        success, stdout, stderr = self.run_etcdctl_command(["member", "list"])
        if not success:
            print(f"Member list check failed: {stderr}")
            return False
        
        member_count = len([line for line in stdout.strip().split('\n') if line.strip()])
        print(f"Cluster is healthy with {member_count} members")
        return True
    
    def cleanup_test_data(self, prefix="/benchmark"):
        """Clean up any existing benchmark data"""
        success, _, _ = self.run_etcdctl_command([
            "del", prefix, "--prefix"
        ])
        return success
    
    def benchmark_sequential_writes(self, count=1000, key_prefix="/benchmark/write"):
        """Benchmark sequential write operations"""
        print(f"Running sequential write benchmark ({count} operations)...")
        
        start_time = time.time()
        failed_ops = 0
        
        for i in range(count):
            key = f"{key_prefix}/key-{i:06d}"
            value = f"value-{i:06d}-{int(time.time() * 1000000)}"
            
            success, _, stderr = self.run_etcdctl_command([
                "put", key, value
            ], timeout=10)
            
            if not success:
                failed_ops += 1
                if failed_ops <= 5:  # Only print first few errors
                    print(f"Write failed for {key}: {stderr}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        successful_ops = count - failed_ops
        ops_per_sec = successful_ops / duration if duration > 0 else 0
        
        return {
            "total_operations": count,
            "successful_operations": successful_ops,
            "failed_operations": failed_ops,
            "duration_seconds": duration,
            "operations_per_second": ops_per_sec,
            "average_latency_ms": (duration * 1000) / successful_ops if successful_ops > 0 else 0
        }
    
    def benchmark_sequential_reads(self, count=1000, key_prefix="/benchmark/write"):
        """Benchmark sequential read operations"""
        print(f"Running sequential read benchmark ({count} operations)...")
        
        start_time = time.time()
        failed_ops = 0
        
        for i in range(count):
            key = f"{key_prefix}/key-{i:06d}"
            
            success, _, stderr = self.run_etcdctl_command([
                "get", key
            ], timeout=10)
            
            if not success:
                failed_ops += 1
                if failed_ops <= 5:  # Only print first few errors
                    print(f"Read failed for {key}: {stderr}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        successful_ops = count - failed_ops
        ops_per_sec = successful_ops / duration if duration > 0 else 0
        
        return {
            "total_operations": count,
            "successful_operations": successful_ops,
            "failed_operations": failed_ops,
            "duration_seconds": duration,
            "operations_per_second": ops_per_sec,
            "average_latency_ms": (duration * 1000) / successful_ops if successful_ops > 0 else 0
        }
    
    def benchmark_concurrent_writes(self, total_ops=1000, concurrency=10, key_prefix="/benchmark/concurrent"):
        """Benchmark concurrent write operations"""
        print(f"Running concurrent write benchmark ({total_ops} operations, {concurrency} threads)...")
        
        ops_per_thread = total_ops // concurrency
        remaining_ops = total_ops % concurrency
        
        results = []
        start_time = time.time()
        
        def worker_thread(thread_id, ops_count):
            thread_results = {"successful": 0, "failed": 0}
            
            for i in range(ops_count):
                key = f"{key_prefix}/thread-{thread_id:02d}/key-{i:06d}"
                value = f"value-{thread_id:02d}-{i:06d}-{int(time.time() * 1000000)}"
                
                success, _, _ = self.run_etcdctl_command([
                    "put", key, value
                ], timeout=10)
                
                if success:
                    thread_results["successful"] += 1
                else:
                    thread_results["failed"] += 1
            
            return thread_results
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = []
            
            for thread_id in range(concurrency):
                ops_count = ops_per_thread + (1 if thread_id < remaining_ops else 0)
                future = executor.submit(worker_thread, thread_id, ops_count)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        end_time = time.time()
        duration = end_time - start_time
        
        total_successful = sum(r["successful"] for r in results)
        total_failed = sum(r["failed"] for r in results)
        ops_per_sec = total_successful / duration if duration > 0 else 0
        
        return {
            "total_operations": total_ops,
            "successful_operations": total_successful,
            "failed_operations": total_failed,
            "duration_seconds": duration,
            "operations_per_second": ops_per_sec,
            "concurrency": concurrency,
            "average_latency_ms": (duration * 1000) / total_successful if total_successful > 0 else 0
        }
    
    def benchmark_mixed_workload(self, duration_seconds=60, read_ratio=0.7):
        """Benchmark mixed read/write workload"""
        print(f"Running mixed workload benchmark ({duration_seconds}s, {read_ratio*100:.0f}% reads)...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        read_count = 0
        write_count = 0
        read_failures = 0
        write_failures = 0
        operation_count = 0
        
        # Pre-populate some data for reads
        for i in range(100):
            key = f"/benchmark/mixed/key-{i:06d}"
            value = f"value-{i:06d}"
            self.run_etcdctl_command(["put", key, value])
        
        while time.time() < end_time:
            operation_count += 1
            
            if (operation_count % 100) == 0:
                # Use modulo for deterministic read/write ratio
                should_read = (operation_count % 10) < (read_ratio * 10)
            else:
                should_read = (operation_count % 10) < (read_ratio * 10)
            
            if should_read:
                # Read operation
                key = f"/benchmark/mixed/key-{operation_count % 100:06d}"
                success, _, _ = self.run_etcdctl_command(["get", key], timeout=5)
                
                if success:
                    read_count += 1
                else:
                    read_failures += 1
            else:
                # Write operation
                key = f"/benchmark/mixed/key-{operation_count:06d}"
                value = f"value-{operation_count:06d}-{int(time.time() * 1000000)}"
                success, _, _ = self.run_etcdctl_command(["put", key, value], timeout=5)
                
                if success:
                    write_count += 1
                else:
                    write_failures += 1
        
        actual_duration = time.time() - start_time
        total_ops = read_count + write_count
        total_ops_per_sec = total_ops / actual_duration if actual_duration > 0 else 0
        
        return {
            "duration_seconds": actual_duration,
            "total_operations": total_ops,
            "read_operations": read_count,
            "write_operations": write_count,
            "read_failures": read_failures,
            "write_failures": write_failures,
            "total_operations_per_second": total_ops_per_sec,
            "read_ops_per_second": read_count / actual_duration if actual_duration > 0 else 0,
            "write_ops_per_second": write_count / actual_duration if actual_duration > 0 else 0,
            "read_ratio_actual": read_count / total_ops if total_ops > 0 else 0
        }
    
    def run_full_benchmark(self, quick=False):
        """Run complete benchmark suite"""
        if not self.check_cluster_health():
            return None
        
        print("Cleaning up any existing benchmark data...")
        self.cleanup_test_data()
        
        benchmark_results = {
            "timestamp": datetime.now().isoformat(),
            "compose_file": self.compose_file,
            "quick_mode": quick
        }
        
        try:
            # Adjust test sizes for quick mode
            if quick:
                write_count = 100
                read_count = 100
                concurrent_ops = 100
                concurrent_threads = 5
                mixed_duration = 10
            else:
                write_count = 1000
                read_count = 1000
                concurrent_ops = 1000
                concurrent_threads = 10
                mixed_duration = 60
            
            # Sequential writes
            print("\n" + "="*50)
            benchmark_results["sequential_writes"] = self.benchmark_sequential_writes(write_count)
            
            # Sequential reads
            print("\n" + "="*50)
            benchmark_results["sequential_reads"] = self.benchmark_sequential_reads(read_count)
            
            # Concurrent writes
            print("\n" + "="*50)
            benchmark_results["concurrent_writes"] = self.benchmark_concurrent_writes(
                concurrent_ops, concurrent_threads
            )
            
            # Mixed workload
            print("\n" + "="*50)
            benchmark_results["mixed_workload"] = self.benchmark_mixed_workload(mixed_duration)
            
            # Cleanup
            print("\nCleaning up benchmark data...")
            self.cleanup_test_data()
            
            return benchmark_results
            
        except KeyboardInterrupt:
            print("\nBenchmark interrupted by user")
            self.cleanup_test_data()
            return None
        except Exception as e:
            print(f"\nBenchmark failed: {e}")
            self.cleanup_test_data()
            return None
    
    def save_results(self, results, filename=None):
        """Save benchmark results to JSON file"""
        if not results:
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {filename}")
        return filename
    
    def print_summary(self, results):
        """Print benchmark results summary"""
        if not results:
            return
        
        print("\n" + "="*60)
        print("BENCHMARK RESULTS SUMMARY")
        print("="*60)
        
        print(f"Timestamp: {results['timestamp']}")
        print(f"Compose file: {results['compose_file']}")
        print(f"Quick mode: {results['quick_mode']}")
        
        if "sequential_writes" in results:
            sw = results["sequential_writes"]
            print(f"\nSequential Writes:")
            print(f"  Operations: {sw['successful_operations']}/{sw['total_operations']}")
            print(f"  Throughput: {sw['operations_per_second']:.2f} ops/sec")
            print(f"  Avg Latency: {sw['average_latency_ms']:.2f} ms")
        
        if "sequential_reads" in results:
            sr = results["sequential_reads"]
            print(f"\nSequential Reads:")
            print(f"  Operations: {sr['successful_operations']}/{sr['total_operations']}")
            print(f"  Throughput: {sr['operations_per_second']:.2f} ops/sec")
            print(f"  Avg Latency: {sr['average_latency_ms']:.2f} ms")
        
        if "concurrent_writes" in results:
            cw = results["concurrent_writes"]
            print(f"\nConcurrent Writes:")
            print(f"  Operations: {cw['successful_operations']}/{cw['total_operations']}")
            print(f"  Concurrency: {cw['concurrency']} threads")
            print(f"  Throughput: {cw['operations_per_second']:.2f} ops/sec")
            print(f"  Avg Latency: {cw['average_latency_ms']:.2f} ms")
        
        if "mixed_workload" in results:
            mw = results["mixed_workload"]
            print(f"\nMixed Workload:")
            print(f"  Duration: {mw['duration_seconds']:.1f} seconds")
            print(f"  Total Ops: {mw['total_operations']}")
            print(f"  Read Ops: {mw['read_operations']} ({mw['read_ratio_actual']*100:.1f}%)")
            print(f"  Write Ops: {mw['write_operations']}")
            print(f"  Total Throughput: {mw['total_operations_per_second']:.2f} ops/sec")
            print(f"  Read Throughput: {mw['read_ops_per_second']:.2f} ops/sec")
            print(f"  Write Throughput: {mw['write_ops_per_second']:.2f} ops/sec")

def main():
    parser = argparse.ArgumentParser(
        description="etcd Cluster Performance Benchmark Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 benchmark.py                           # Run full benchmark
  python3 benchmark.py --quick                   # Run quick benchmark
  python3 benchmark.py -f cluster-5.yml         # Benchmark specific cluster
  python3 benchmark.py --output results.json    # Save to specific file
        """
    )
    
    parser.add_argument(
        "-f", "--compose-file",
        default="docker-compose-generated.yml",
        help="Docker Compose file to use (default: docker-compose-generated.yml)"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick benchmark with reduced test sizes"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file for results (default: auto-generated)"
    )
    
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Don't print results summary"
    )
    
    args = parser.parse_args()
    
    # Check if compose file exists
    if not Path(args.compose_file).exists():
        print(f"Error: Compose file not found: {args.compose_file}")
        print("Generate a cluster first using: ./cluster-manager.sh generate <nodes>")
        sys.exit(1)
    
    benchmark = EtcdBenchmark(args.compose_file)
    
    print("Starting etcd cluster benchmark...")
    if args.quick:
        print("Running in quick mode (reduced test sizes)")
    
    results = benchmark.run_full_benchmark(quick=args.quick)
    
    if results:
        if not args.no_summary:
            benchmark.print_summary(results)
        
        benchmark.save_results(results, args.output)
    else:
        print("Benchmark failed or was interrupted")
        sys.exit(1)

if __name__ == "__main__":
    main()
