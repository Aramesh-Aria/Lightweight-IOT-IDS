"""Project-wide constants: paths, seeds, k values, dropped columns, class mapping."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATA_FILE = DATA_DIR / "ML-EdgeIIoT-dataset.csv"
RESULTS_DIR = PROJECT_ROOT / "results"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"

# Experiment protocol
SEEDS = [42, 0, 1, 2, 3]
MAIN_SEED = 42
K_VALUES = [5, 6, 7, 8, 10, 15, 20]
TEST_SIZE = 0.20  # share of the full data held out for testing
VAL_SIZE = 0.20   # share of the training data held out for validation (PFI)

# Label columns
TYPE_COLUMN = "Attack_type"
BINARY_LABEL_COLUMN = "Attack_label"  # binary label, never used as input

# 19 columns removed by the main paper (Section 4.1)
DROP_COLUMNS = [
    "frame.time",
    "ip.src_host",
    "ip.dst_host",
    "arp.dst.proto_ipv4",
    "arp.src.proto_ipv4",
    "http.file_data",
    "http.request.uri.query",
    "http.request.method",
    "http.referer",
    "http.request.full_uri",
    "http.request.version",
    "tcp.options",
    "tcp.payload",
    "tcp.srcport",
    "dns.qry.name.len",
    "mqtt.conack.flags",
    "mqtt.msg",
    "mqtt.protoname",
    "mqtt.topic",
]

N_FEATURES = 42

# Attack type -> class (Ferrag et al. 2022 grouping)
ATTACK_TYPE_TO_CLASS = {
    "Normal": "Normal",
    "DDoS_UDP": "DDoS",
    "DDoS_ICMP": "DDoS",
    "DDoS_HTTP": "DDoS",
    "DDoS_TCP": "DDoS",
    "Vulnerability_scanner": "Information gathering",
    "Port_Scanning": "Information gathering",
    "Fingerprinting": "Information gathering",
    "MITM": "MITM",
    "SQL_injection": "Injection",
    "Uploading": "Injection",
    "XSS": "Injection",
    "Ransomware": "Malware",
    "Backdoor": "Malware",
    "Password": "Malware",
}

CLASS_ORDER = [
    "Normal",
    "DDoS",
    "Information gathering",
    "MITM",
    "Injection",
    "Malware",
]

# Expected class counts (Table 3 of the main paper)
EXPECTED_CLASS_COUNTS = {
    "Normal": 24301,
    "DDoS": 49396,
    "Information gathering": 21148,
    "MITM": 1214,
    "Injection": 30632,
    "Malware": 31109,
}

# Constant-valued columns among the 42 features (kept, see Q26)
CONSTANT_COLUMNS = [
    "icmp.unused",
    "http.tls_port",
    "dns.qry.type",
    "dns.retransmit_request_in",
    "mqtt.msg_decoded_as",
    "mbtcp.len",
    "mbtcp.trans_id",
    "mbtcp.unit_id",
]

# The 8 top features reported by the main paper (k=8)
PAPER_TOP8 = [
    "tcp.dstport",
    "tcp.ack",
    "tcp.seq",
    "tcp.len",
    "tcp.checksum",
    "tcp.ack_raw",
    "tcp.flags",
    "tcp.flags.ack",
]
