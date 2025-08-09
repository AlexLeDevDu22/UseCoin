import configparser

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

difficulty = int(config["TEST"]["START_DIFFICULTY"], 16)

def reward_job(blockchain, miner_id, timestamp):
    if int(blockchain.compute_hash_mempool(timestamp, miner_id, difficulty), 16) < difficulty:
        return True
    return False

def adjust_difficulty(blockchain):
    adjust_interval = config["TEST"]["DIFF_ADJUST_INTERVAL"]
    if len(blockchain.chain) % adjust_interval != 0:
        return  # pas encore le moment d'ajuster

    start_block = blockchain.chain[-adjust_interval]
    last_block = blockchain.get_last_block()
    elapsed_time = last_block.timestamp - start_block.timestamp

    expected_time = config["TEST"]["TARGET_BLOCK_TIME"] * adjust_interval
    ratio = elapsed_time / expected_time

    # ajustement proportionnel
    difficulty = int(difficulty * ratio)

    # clamp la target pour éviter valeurs folles
    max_target = int("00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", 16)
    min_target = 1
    difficulty = max(min_target, min(max_target, difficulty))

    print(f"[Diff] Temps moyen: {elapsed_time/adjust_interval:.2f}s | Ratio: {ratio:.2f} | Nouvelle target: {hex(difficulty)}")
