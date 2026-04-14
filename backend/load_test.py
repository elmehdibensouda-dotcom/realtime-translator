import asyncio
import json
import time
import websockets
import statistics

# Configuration
WS_URL = "ws://localhost:8080/ws/translate?token=test-token"
CONCURRENT_USERS = 10  # Nombre d'utilisateurs simulés
MESSAGES_PER_USER = 20 # Nombre de phrases par utilisateur
MESSAGE_DELAY = 1      # Délai entre les phrases (secondes)

async def simulate_user(user_id, results):
    latencies = []
    try:
        async with websockets.connect(WS_URL) as ws:
            for i in range(MESSAGES_PER_USER):
                start_time = time.perf_counter()
                
                # Simulation d'une phrase type meeting
                text = f"User {user_id} is saying sentence number {i} to test the latency of the translation engine."
                await ws.send(json.dumps({
                    "text": text,
                    "is_final": True,
                    "seq_id": i
                }))
                
                # Attente de la réponse
                response = await ws.recv()
                end_time = time.perf_counter()
                
                latency = (end_time - start_time) * 1000
                latencies.append(latency)
                
                await asyncio.sleep(MESSAGE_DELAY)
                
        results[user_id] = latencies
        print(f"✅ User {user_id} finished. Avg Latency: {statistics.mean(latencies):.2f}ms")
    except Exception as e:
        print(f"❌ User {user_id} failed: {e}")

async def run_benchmark():
    print(f"🚀 Starting Load Test: {CONCURRENT_USERS} users, {MESSAGES_PER_USER} messages each...")
    results = {}
    tasks = [simulate_user(i, results) for i in range(CONCURRENT_USERS)]
    
    start_bench = time.perf_counter()
    await asyncio.gather(*tasks)
    end_bench = time.perf_counter()
    
    # Calcul des stats globales
    all_latencies = [l for user_l in results.values() for l in user_l]
    if all_latencies:
        print("\n--- GLOBAL RESULTS ---")
        print(f"Total Time: {end_bench - start_bench:.2f}s")
        print(f"Avg Latency: {statistics.mean(all_latencies):.2f}ms")
        print(f"Min Latency: {min(all_latencies):.2f}ms")
        print(f"Max Latency: {max(all_latencies):.2f}ms")
        print(f"P95 Latency: {statistics.quantiles(all_latencies, n=20)[18]:.2f}ms")
        print("----------------------\n")

if __name__ == "__main__":
    # Note: Assurez-vous que le backend tourne avant de lancer ce script
    try:
        asyncio.run(run_benchmark())
    except KeyboardInterrupt:
        pass
