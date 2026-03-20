"""Style vocabularies and widget content pools for FakeData Terminal."""

import random


# ── Shared numeric helpers ─────────────────────────────────────────────────────

HEX_CHARS = "0123456789ABCDEF"
B64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="

HEX_WORD  = lambda n=8: "0x" + "".join(random.choices(HEX_CHARS, k=n))
HEX_BLOCK = lambda n=None: " ".join(
    "".join(random.choices(HEX_CHARS, k=2))
    for _ in range(n or random.randint(6, 12))
)
B64_CHUNK = lambda w=30: "".join(
    random.choices(B64_CHARS, k=random.randint(max(4, w - 6), w + 6))
)
PERCENT   = lambda: f"{random.randint(0,100):3d}%"
TIMESTAMP = lambda: (f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:"
                     f"{random.randint(0,59):02d}.{random.randint(0,999):03d}")
SCI_FLOAT = lambda: f"{random.uniform(1e-12, 9.99e12):.4e}"

# ══════════════════════════════════════════════════════════════════════════════
# STYLE: hacker
# ══════════════════════════════════════════════════════════════════════════════

_H_PROTOCOLS = ["TCP","UDP","SSH","TLS","SSL","HTTP","HTTPS","FTP","SMTP","DNS",
                "ICMP","ARP","BGP","OSPF","IMAP","POP3","SNMP","LDAP","RPC","SMB"]
_H_ACTIONS   = ["SCANNING","PROBING","INJECTING","BYPASSING","DECRYPTING",
                "ENCRYPTING","TUNNELING","SPOOFING","SNIFFING","ROUTING",
                "PATCHING","EXPLOITING","PIVOTING","ENUMERATING","FUZZING",
                "BRUTE-FORCING","ESCALATING","EXFILTRATING","OBFUSCATING",
                "COMPILING","LINKING","DEPLOYING","INITIALIZING","TERMINATING"]
_H_TARGETS   = ["firewall","kernel module","root certificate","JWT token",
                "RSA-4096 keypair","AES-256 block","SHA-512 hash","BIOS interrupt",
                "EFI partition","memory map","stack frame","heap segment",
                "syscall table","inode","socket buffer","TLS handshake",
                "session cookie","OAuth token","DNS cache","routing table",
                "subnet mask","NAT table","iptables rule","cron daemon",
                "syslog pipe","PAM module","LDAP directory","X.509 cert"]
_H_STATUSES  = ["OK","DONE","PASS","FAIL","WARN","ERR","200","301","403","404",
                "500","ACK","RST","SYN","FIN","TIMEOUT","RETRYING","ACCEPTED",
                "REJECTED","PENDING","QUEUED","ACTIVE","DEAD","ALIVE","STALE"]
_H_FILENAMES = ["/etc/shadow","/proc/self/mem","/dev/null","/boot/vmlinuz",
                "/sys/kernel/debug","~/.ssh/id_rsa","~/.bash_history",
                "/var/log/auth.log","/tmp/.x11-lock","/run/secrets/token",
                "/etc/crontab","/lib/x86_64-linux-gnu/libc.so.6",
                "0x7fff...stack","[vdso]","[heap]","[stack]"]
_H_IPS  = lambda: (f"{random.randint(1,254)}.{random.randint(0,254)}."
                   f"{random.randint(0,254)}.{random.randint(1,254)}")
_H_PORT = lambda: random.randint(1, 65535)
_H_PID  = lambda: random.randint(1, 65535)

def _h_line_network():
    proto = random.choice(_H_PROTOCOLS)
    return (f"[{TIMESTAMP()}] {proto:5s}  {_H_IPS()}:{_H_PORT()}"
            f" -> {_H_IPS()}:{_H_PORT()}  {random.choice(_H_STATUSES)}")

def _h_line_action():
    return (f"[{TIMESTAMP()}] {random.choice(_H_ACTIONS)}"
            f" {random.choice(_H_TARGETS)} ... {random.choice(_H_STATUSES)}")

def _h_line_hex():
    tail = "".join(random.choices("abcdefghijklmnopqrstuvwxyz./,;", k=16))
    return f"{HEX_WORD(8)}:  {HEX_BLOCK()}  |{tail}|"

def _h_line_progress():
    pct = PERCENT()
    filled = int(20 * int(pct.strip('%')) / 100)
    bar = "#" * filled + "." * (20 - filled)
    return f"{random.choice(_H_ACTIONS):>20s}  [{bar}] {pct}"

def _h_line_process():
    return (f"PID {_H_PID():>5d}  CPU {PERCENT()}  MEM {PERCENT()}  "
            f"{random.choice(_H_ACTIONS).lower()[:12]:<12s}  {random.choice(_H_FILENAMES)}")

def _h_line_b64():
    label = random.choice(["PAYLOAD","TOKEN","CERT","HASH","KEY","BLOB","DATA"])
    return f"  [{label}]  {B64_CHUNK(36)}"

def _h_line_error():
    codes = ["SEGFAULT","SIGKILL","EACCES","ENOMEM","ENOENT","EPERM","EBUSY",
             "EIO","ETIMEDOUT","ECONNREFUSED","EADDRINUSE","EOVERFLOW"]
    return (f"!! {random.choice(codes)} at {HEX_WORD(16)}"
            f"  (pid {_H_PID()})  -- {random.choice(_H_TARGETS)}")

def _h_line_kernel():
    subsys = random.choice(["net","mm","fs","sched","crypto","usb","pci","irq"])
    return (f"[{random.uniform(0, 99999):.6f}] kernel/{subsys}: "
            f"{random.choice(_H_ACTIONS).lower()} {HEX_WORD()} flags={HEX_WORD(4)}")

def _h_line_raw_hex():
    return "  " + "  ".join(HEX_WORD(4) for _ in range(random.randint(4, 8)))

def _h_rcol_hex():    return f"{HEX_WORD(8)}: {HEX_BLOCK(5)}"
def _h_rcol_stat():   return f"{random.choice(_H_STATUSES):>10s}  {HEX_WORD(4)}"
def _h_rcol_net():    return f"{_H_IPS()}:{_H_PORT()}"
def _h_rcol_b64():    return B64_CHUNK(20)
def _h_rcol_action(): return f"{random.choice(_H_ACTIONS)[:18]}..."
def _h_rcol_pid():    return f"pid={_H_PID():>5d} {PERCENT()} {PERCENT()}"
def _h_rcol_addr():   return HEX_WORD(16)

_H_GENERATORS = [
    (_h_line_network,  18), (_h_line_action,   18), (_h_line_hex,      14),
    (_h_line_progress, 10), (_h_line_process,  12), (_h_line_b64,       8),
    (_h_line_error,     6), (_h_line_kernel,   10), (_h_line_raw_hex,   4),
]
_H_RCOL_POOL = (
    [_h_rcol_hex]*20 + [_h_rcol_stat]*15 + [_h_rcol_net]*15 +
    [_h_rcol_b64]*15 + [_h_rcol_action]*15 + [_h_rcol_pid]*10 + [_h_rcol_addr]*10
)

# ══════════════════════════════════════════════════════════════════════════════
# STYLE: science  (particle physics / quantum / cosmology)
# ══════════════════════════════════════════════════════════════════════════════

_S_PARTICLES  = ["quark","gluon","neutrino","muon","tau","boson","fermion",
                 "photon","graviton","Higgs field","dark matter","antiproton",
                 "positron","pion","kaon","lambda baryon","charm quark","top quark"]
_S_ACTIONS    = ["COLLIDING","ENTANGLING","SUPERPOSING","DECOHERING","TUNNELING",
                 "OSCILLATING","ANNIHILATING","PROPAGATING","INTERFERING",
                 "SCATTERING","ABSORBING","EMITTING","MEASURING","COLLAPSING",
                 "COMPRESSING","EXPANDING","DIFFRACTING","POLARIZING","EXCITING"]
_S_OBSERV     = ["spin","momentum","energy","charge","parity","mass","wavelength",
                 "amplitude","phase","coherence","entanglement-entropy","flux",
                 "cross-section","decay-rate","coupling-const","eigenvalue"]
_S_DETECTORS  = ["calorimeter","tracker","Cherenkov-array","scintillator",
                 "drift-chamber","pixel-detector","muon-spectrometer","TOF-array",
                 "silicon-vertex","ECAL","HCAL","forward-detector","wire-chamber"]
_S_STATUSES   = ["STABLE","UNSTABLE","DECAY","RESONANCE","ANOMALY","NOMINAL",
                 "EXCEEDED","BELOW-THRESH","CONFIRMED","UNCONFIRMED","LOST",
                 "RECONSTRUCTED","FLAGGED","SATURATED","MASKED","TRIGGERED"]
_S_UNITS      = ["eV","keV","MeV","GeV","TeV","fm","pb","nb","T","Wb","Hz","s"]

def _s_line_event():
    e    = random.randint(10000000, 99999999)
    lumi = random.uniform(1e30, 9.9e34)
    return (f"[EVT {e}] {random.choice(_S_DETECTORS):<22s}"
            f"  L={lumi:.3e}  {random.choice(_S_STATUSES)}")

def _s_line_particle():
    p1 = random.choice(_S_PARTICLES)
    p2 = random.choice(_S_PARTICLES)
    e  = random.uniform(0.1, 14000)
    return (f"[{TIMESTAMP()}] {random.choice(_S_ACTIONS)}"
            f"  {p1} + {p2}  E={e:.2f} {random.choice(_S_UNITS)}")

def _s_line_measurement():
    obs = random.choice(_S_OBSERV)
    val = SCI_FLOAT()
    unc = random.uniform(1e-6, 0.1)
    return f"  {obs:<24s}  =  {val}  +-{unc:.2e}  {random.choice(_S_UNITS)}"

def _s_line_waveform():
    vals = "  ".join(f"{random.gauss(0, 1):+.4f}" for _ in range(6))
    return f"  psi[{random.randint(0,63):02d}]  {vals}"

def _s_line_decay():
    p        = random.choice(_S_PARTICLES)
    products = " + ".join(random.choices(_S_PARTICLES, k=random.randint(2, 3)))
    t_half   = random.uniform(1e-25, 1e10)
    return f"  DECAY  {p:<18s}  ->  {products:<26s}  t1/2={t_half:.3e}s"

def _s_line_channel():
    ch     = f"CH{random.randint(0, 511):03d}"
    counts = "  ".join(f"{random.randint(0, 4095):4d}" for _ in range(8))
    return f"  {ch}  [{counts}]"

def _s_line_alert():
    codes = ["BEAM-LOSS","QUENCH","TRIP","INTERLOCK","ABORT","RF-FAULT",
             "VACUUM-LOSS","MAGNET-FAULT","TIMING-ERR","SYNC-FAIL"]
    return (f"!! {random.choice(codes)}  {random.choice(_S_DETECTORS)}"
            f"  t={TIMESTAMP()}  -- {random.choice(_S_STATUSES)}")

def _s_line_matrix():
    row = "  ".join(f"{random.gauss(0, 0.5):+.3f}" for _ in range(7))
    return f"  |  {row}  |"

def _s_rcol_val():
    return f"{random.choice(_S_OBSERV)[:14]:<14s} {SCI_FLOAT()}"
def _s_rcol_ch():
    return f"CH{random.randint(0,511):03d}  {random.randint(0,65535):5d} cts"
def _s_rcol_status():
    return f"{random.choice(_S_STATUSES):>14s}"
def _s_rcol_psi():
    return f"p={random.gauss(0,1):+.5f}+{random.gauss(0,1):+.5f}i"
def _s_rcol_energy():
    return f"E={random.uniform(0, 14000):8.3f} {random.choice(_S_UNITS)}"
def _s_rcol_particle():
    return f"{random.choice(_S_PARTICLES)[:20]}"

_S_GENERATORS = [
    (_s_line_event,       18), (_s_line_particle,    18), (_s_line_measurement, 16),
    (_s_line_waveform,    12), (_s_line_decay,        12), (_s_line_channel,     12),
    (_s_line_alert,        6), (_s_line_matrix,        6),
]
_S_RCOL_POOL = (
    [_s_rcol_val]*20 + [_s_rcol_ch]*20 + [_s_rcol_status]*15 +
    [_s_rcol_psi]*15 + [_s_rcol_energy]*15 + [_s_rcol_particle]*15
)

# ══════════════════════════════════════════════════════════════════════════════
# STYLE: medical  (patient monitoring / biosystems)
# ══════════════════════════════════════════════════════════════════════════════

_M_VITALS    = ["HR","SpO2","BP_SYS","BP_DIA","RR","TEMP","EtCO2","MAP","CVP",
                "ICP","SvO2","ScvO2","PI","PVI","NIBP"]
_M_SYSTEMS   = ["cardiovascular","respiratory","neurological","renal","hepatic",
                "endocrine","haematological","immunological","gastrointestinal",
                "musculoskeletal","dermal","lymphatic","autonomic"]
_M_PROCESSES = ["MONITORING","SAMPLING","ANALYZING","CALIBRATING","TRENDING",
                "ALERTING","RECORDING","FILTERING","CORRELATING","COMPUTING",
                "INTEGRATING","CROSS-REFERENCING","VALIDATING","FLAGGING",
                "NORMALIZING","INTERPOLATING","PREDICTING","CLASSIFYING"]
_M_DRUGS     = ["adrenaline","noradrenaline","dopamine","dobutamine","heparin",
                "morphine","propofol","midazolam","fentanyl","vancomycin",
                "amiodarone","atropine","metoprolol","furosemide","insulin"]
_M_COMPOUNDS = ["haemoglobin","troponin-I","BNP","lactate","creatinine","urea",
                "albumin","fibrinogen","D-dimer","CRP","IL-6","procalcitonin",
                "cortisol","glucose","pH","pCO2","pO2","HCO3","electrolytes"]
_M_WAVEFORMS = ["ECG-I","ECG-II","ECG-V1","ECG-V5","PLETH","EEG-Fp1","EEG-Cz",
                "ABP-wave","CVP-wave","PAP-wave","CAPNO","FLOW"]
_M_STATUSES  = ["NORMAL","BORDERLINE","ELEVATED","REDUCED","CRITICAL","STABLE",
                "IMPROVING","DETERIORATING","ARRHYTHMIA","ECTOPIC","ARTIFACT",
                "SIGNAL-LOSS","RECALIBRATING","VALID","INVALID","TRENDING-UP",
                "TRENDING-DOWN","ALARM","ALERT","SUPPRESSED"]
_M_UNITS     = ["bpm","mmHg","degC","%","mmol/L","umol/L","mg/dL","mL/hr",
                "ng/mL","pg/mL","IU/L","mEq/L","kPa","cmH2O"]

def _m_vital_sign():
    v    = random.choice(_M_VITALS)
    val  = random.uniform(0, 200)
    unit = random.choice(_M_UNITS)
    return (f"[{TIMESTAMP()}]  {v:<8s}  {val:7.2f} {unit:<8s}"
            f"  {random.choice(_M_STATUSES)}")

def _m_system():
    return (f"[{TIMESTAMP()}] {random.choice(_M_PROCESSES)}"
            f" {random.choice(_M_SYSTEMS)} system ... {random.choice(_M_STATUSES)}")

def _m_lab():
    cmpd   = random.choice(_M_COMPOUNDS)
    val    = random.uniform(0.001, 999)
    unit   = random.choice(_M_UNITS)
    ref_lo = random.uniform(0, 400)
    ref_hi = ref_lo + random.uniform(10, 200)
    flag   = "  *" if val < ref_lo or val > ref_hi else "   "
    return (f"  {cmpd:<18s}  {val:8.3f} {unit:<8s}"
            f"  ref [{ref_lo:.1f}-{ref_hi:.1f}]{flag}")

def _m_waveform():
    ch   = random.choice(_M_WAVEFORMS)
    vals = "  ".join(f"{random.gauss(0, 0.8):+.3f}" for _ in range(7))
    return f"  {ch:<14s}  {vals}"

def _m_drug():
    drug = random.choice(_M_DRUGS)
    rate = random.uniform(0.01, 50)
    conc = random.uniform(0.1, 10)
    return (f"  INFUSION  {drug:<14s}  {rate:.2f} mL/hr"
            f"  @ {conc:.1f} mg/mL  {random.choice(_M_STATUSES)}")

def _m_trend():
    cmpd = random.choice(_M_COMPOUNDS)
    vals = "  ".join(f"{random.uniform(0, 200):.1f}" for _ in range(6))
    return f"  TREND {cmpd:<16s}  [{vals}]"

def _m_alarm():
    codes = ["ASYSTOLE","VF","VT","BRADYCARDIA","TACHYCARDIA","APNOEA",
             "HYPOXIA","HYPOTENSION","HYPERTENSION","HYPERGLYCAEMIA",
             "HYPOGLYCAEMIA","HAEMORRHAGE","SEPSIS-ALERT","DRUG-LIMIT"]
    return (f"!! ALARM  {random.choice(codes):<18s}"
            f"  {random.choice(_M_VITALS)}={random.uniform(0,200):.1f}"
            f"  t={TIMESTAMP()}")

def _m_spectrum():
    row = "  ".join(f"{random.uniform(0, 1):.3f}" for _ in range(8))
    return f"  PSD  [{row}]"

def _m_rcol_vital():
    return f"{random.choice(_M_VITALS):<8s} {random.uniform(0,200):6.1f} {random.choice(_M_UNITS)}"
def _m_rcol_status():
    return f"{random.choice(_M_STATUSES):>16s}"
def _m_rcol_compound():
    return f"{random.choice(_M_COMPOUNDS)[:18]}"
def _m_rcol_wave():
    return f"{random.choice(_M_WAVEFORMS):<12s} {random.gauss(0,1):+.4f}"
def _m_rcol_infusion():
    return f"{random.choice(_M_DRUGS)[:12]:<12s} {random.uniform(0,50):.1f}mL/h"

_M_GENERATORS = [
    (_m_vital_sign, 20), (_m_system,   16), (_m_lab,      16),
    (_m_waveform,   14), (_m_drug,     10), (_m_trend,     8),
    (_m_alarm,       6), (_m_spectrum,  6),
]
_M_RCOL_POOL = (
    [_m_rcol_vital]*25 + [_m_rcol_status]*20 + [_m_rcol_compound]*20 +
    [_m_rcol_wave]*20   + [_m_rcol_infusion]*15
)


# ══════════════════════════════════════════════════════════════════════════════
# STYLE: pharmacy  (dispensary workflow / adjudication / therapeutic monitoring)
# ══════════════════════════════════════════════════════════════════════════════

_P_PRODUCTS = [
    ("amoxicillin",      "500mg",     "CAP"),
    ("atorvastatin",     "20mg",      "TAB"),
    ("metformin",        "500mg",     "TAB"),
    ("levothyroxine",    "50mcg",     "TAB"),
    ("ramipril",         "10mg",      "CAP"),
    ("sertraline",       "100mg",     "TAB"),
    ("salbutamol",       "100mcg",    "INH"),
    ("apixaban",         "5mg",       "TAB"),
    ("insulin glargine", "100U/mL",   "PEN"),
    ("vancomycin",       "250mg",     "CAP"),
    ("digoxin",          "0.125mg",   "TAB"),
    ("lithium carbonate","300mg",     "CAP"),
    ("phenytoin",        "100mg",     "CAP"),
    ("tacrolimus",       "1mg",       "CAP"),
]
_P_SIGS = [
    "1 tab BID", "1 tab daily", "2 tabs BID", "1 cap TID", "1 tab HS",
    "1-2 tabs q6h PRN", "10u SC HS", "5u SC AC meals", "2 puffs q4h PRN",
    "as directed", "apply daily", "1 cap q8h"
]
_P_QUEUE_STATES = [
    "ORDERED", "ADJUDICATION", "FILLING", "PHARMACIST-VERIFY", "READY",
    "PICKED-UP", "DENIED", "CONFIRMATION REQUIRED", "SPECIAL AUTHORITY",
    "DUR OVERRIDE", "REFILL TOO SOON", "PA REQUIRED", "TRANSFER PENDING"
]
_P_DENIAL_REASONS = [
    "SPECIAL AUTHORITY REQUIRED", "MAX DOSE EXCEEDED", "DRUG INTERACTION",
    "REFILL TOO SOON", "PLAN LIMIT", "INVALID DIN", "PATIENT MISMATCH",
    "MISSING PRESCRIBER ID", "PA EXPIRED", "DUPLICATE CLAIM"
]
_P_PLANS = ["PHARMANET", "PACIFIC BLUE", "SUNLIFE", "GREENSHIELD", "CASH"]
_P_BINS = ["A12", "B03", "C44", "D19", "E07", "F28", "G31", "H22"]
_P_TDM_RANGES = {
    "vancomycin": (10.0, 20.0, "mg/L"),
    "digoxin": (0.8, 2.0, "mcg/L"),
    "lithium carbonate": (0.6, 1.2, "mmol/L"),
    "phenytoin": (10.0, 20.0, "mg/L"),
    "tacrolimus": (5.0, 15.0, "mcg/L"),
}

def _p_rxnum():
    return f"Rx{random.randint(1000000, 9999999)}"

def _p_din():
    return f"{random.randint(10000000, 99999999)}"

def _p_pid():
    return f"PT-{random.randint(10000,99999)}"

def _p_product():
    return random.choice(_P_PRODUCTS)

def _p_status():
    return random.choice(_P_QUEUE_STATES)

def _p_line_ordered():
    drug, strength, form = _p_product()
    qty = random.choice([14, 21, 28, 30, 56, 60, 84, 90, 100])
    rfx = random.randint(0, 5)
    return (f"[{TIMESTAMP()}] ORDERED  {_p_rxnum()}  DIN {_p_din()}  "
            f"{drug:<18s} {strength:<8s} {form:<4s}  qty {qty:<3d}  "
            f"rfx {rfx}  sig '{random.choice(_P_SIGS)}'")

def _p_line_adjudication():
    drug, strength, form = _p_product()
    copay = random.uniform(0, 120)
    dur = random.choice(["PASS", "WARN", "BLOCK", "OVERRIDE"])
    return (f"[{TIMESTAMP()}] ADJUDICATION  {_p_rxnum()}  {drug:<18s} {strength:<8s} {form:<4s}  "
            f"plan={random.choice(_P_PLANS):<12s}  copay=${copay:6.2f}  DUR={dur:<8s}  {_p_status()}")

def _p_line_fill():
    drug, strength, form = _p_product()
    lot = f"L{random.randint(100000,999999)}"
    exp_y = random.randint(2026, 2031)
    exp_m = random.randint(1, 12)
    return (f"  FILLING  {_p_rxnum()}  {drug:<18s} {strength:<8s} {form:<4s}  "
            f"bin {random.choice(_P_BINS):<3s}  lot {lot}  exp {exp_y:04d}-{exp_m:02d}")

def _p_line_verify():
    drug, strength, form = _p_product()
    checks = random.choice(["ID+ALLERGY", "DIN+SIG", "QTY+LOT", "DUR+COUNSEL"])
    initials = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
    return (f"[{TIMESTAMP()}] PHARMACIST-VERIFY  {_p_rxnum()}  {drug:<18s} {strength:<8s} {form:<4s}  "
            f"{checks:<12s}  RPh {initials}  {random.choice(['PASS','PASS','PASS','HOLD'])}")

def _p_line_pickup():
    wait = random.randint(1, 240)
    return (f"[{TIMESTAMP()}] PICKED-UP  {_p_rxnum()}  {_p_pid()}  "
            f"wait={wait:3d}m  counselling={random.choice(['DONE','DECLINED','REQUIRED'])}")

def _p_line_dose_check():
    drug, strength, form = _p_product()
    qty = random.choice([14, 21, 28, 30, 56, 60, 84, 90, 100])
    mdd = random.choice(["1/day", "2/day", "3/day", "q6h max 4", "q8h max 3"])
    return (f"  DOSE-CHECK  {_p_rxnum()}  {drug:<18s} {strength:<8s} {form:<4s}  "
            f"sig '{random.choice(_P_SIGS):<18s}'  qty {qty:<3d}  max {mdd:<10s}  "
            f"{random.choice(['OK','REVIEW','HOLD'])}")

def _p_line_exception():
    return (f"!! {random.choice(['DENIED','HOLD','REJECTED'])}  {_p_rxnum()}  "
            f"DIN {_p_din()}  reason: {random.choice(_P_DENIAL_REASONS)}")

def _p_line_serum():
    drug = random.choice(list(_P_TDM_RANGES.keys()))
    lo, hi, unit = _P_TDM_RANGES[drug]
    val = random.uniform(lo * 0.5, hi * 1.6)
    if val < lo:
        flag = "LOW"
    elif val > hi:
        flag = "HIGH"
    else:
        flag = "IN-RANGE"
    trend = "  ".join(f"{random.uniform(lo*0.6, hi*1.4):.2f}" for _ in range(4))
    return (f"  SERUM  {drug:<18s} {val:6.2f} {unit:<7s}  ref [{lo:.2f}-{hi:.2f}]  "
            f"{flag:<8s}  trend [{trend}]")

def _p_line_spike2():
    chan = random.randint(1, 16)
    sample = f"S{random.randint(1000,9999)}"
    assay = random.choice(["VANC", "DIG", "LITH", "PHT", "TAC", "CRP", "INR"])
    th = random.uniform(0.2, 99.9)
    return (f"  spike2: ch{chan:02d}  sample={sample}  assay={assay:<4s}  "
            f"threshold={th:5.2f}  {random.choice(['capture','hold','emit','flag'])}")

_P_SPIKE_VARS = [
    "ch", "sample_id", "assay", "level", "hi", "lo", "din", "rx", "qc",
    "delta", "window", "buf", "trace", "ok", "result", "flags"
]
_P_SPIKE_FUNCS = [
    "read_adc", "run_assay", "queue_sample", "flag_result", "emit_event",
    "calc_serum", "verify_din", "push_claim", "log_result", "qc_check",
    "apply_filter", "save_trace", "load_calibration", "warn", "hold_rx"
]

def _p_code_decl():
    typ = random.choice(["int", "float", "string", "array(float)", "mapping"])
    name = random.choice(_P_SPIKE_VARS)
    if typ == "int":
        val = str(random.randint(0, 999))
    elif typ == "float":
        val = f"{random.uniform(0.0, 99.9):.3f}"
    elif typ == "string":
        val = f"\"S{random.randint(1000,9999)}\""
    elif typ == "array(float)":
        val = "({ " + ", ".join(f"{random.uniform(0.1, 9.9):.2f}" for _ in range(3)) + " })"
    else:
        val = "([ \"rx\" : 0, \"din\" : 0 ])"
    return f"{typ} {name} = {val};"

def _p_code_if():
    lhs = random.choice(_P_SPIKE_VARS)
    rhs = random.choice([str(random.randint(1, 50)), f"{random.uniform(0.5, 20.0):.2f}"])
    op = random.choice([">", "<", ">=", "<=", "==", "!="])
    fn = random.choice(_P_SPIKE_FUNCS)
    arg = random.choice(_P_SPIKE_VARS)
    return f"if ({lhs} {op} {rhs}) {fn}({arg});"

def _p_code_call():
    fn = random.choice(_P_SPIKE_FUNCS)
    argc = random.randint(1, 3)
    args = ", ".join(random.choice(_P_SPIKE_VARS) for _ in range(argc))
    return f"{fn}({args});"

def _p_code_loop():
    lim = random.randint(4, 32)
    fn = random.choice(_P_SPIKE_FUNCS)
    return f"for (int i = 0; i < {lim}; i++) {fn}(buf[i]);"

def _p_code_comment():
    txt = random.choice([
        "normalize serum trace before adjudication",
        "reject refill when window < minimum interval",
        "special authority branch for lithium",
        "delta guard to prevent noisy false highs",
        "push qc marker for failed calibration",
        "re-check DIN map after transfer merge",
    ])
    return f"// {txt}"

def _p_rcol_rx():
    return f"{_p_rxnum():<11s} {random.choice(['ORDERED','FILLING','READY','HOLD']):>8s}"
def _p_rcol_din():
    drug, _, _ = _p_product()
    return f"DIN {_p_din()} {drug[:14]}"
def _p_rcol_queue():
    return f"Q in={random.randint(0,45):2d} vrf={random.randint(0,18):2d} rdy={random.randint(0,28):2d}"
def _p_rcol_serum():
    drug = random.choice(list(_P_TDM_RANGES.keys()))
    lo, hi, unit = _P_TDM_RANGES[drug]
    val = random.uniform(lo * 0.6, hi * 1.3)
    return f"{drug[:10]:<10s} {val:5.2f}{unit}"
def _p_rcol_spike():
    return f"spk2 ch{random.randint(1,16):02d} {random.choice(['arm','run','qc','flag'])}"

_P_GENERATORS = [
    (_p_line_ordered,      22), (_p_line_adjudication, 18), (_p_line_fill,        16),
    (_p_line_verify,       14), (_p_line_dose_check,   14), (_p_line_pickup,       8),
    (_p_line_exception,     8), (_p_line_serum,        10), (_p_line_spike2,        8),
]
_P_RCOL_POOL = (
    [_p_rcol_rx]*25 + [_p_rcol_din]*20 + [_p_rcol_queue]*20 +
    [_p_rcol_serum]*20 + [_p_rcol_spike]*15
)
_P_MAIN_TEXT_GENERATORS = [
    (_p_line_ordered,      26), (_p_line_adjudication, 22), (_p_line_fill,        20),
    (_p_line_verify,       18), (_p_line_dose_check,   20), (_p_line_pickup,       6),
    (_p_line_exception,     6), (_p_line_serum,        10),
]
_P_MAIN_GEN_POOL = [g for g, w in _P_MAIN_TEXT_GENERATORS for _ in range(w)]
_P_MAIN_RCOL_POOL = (
    [_p_rcol_rx]*25 + [_p_rcol_din]*20 + [_p_rcol_queue]*20 + [_p_rcol_serum]*20
)
_P_SIDEBAR_SPIKE_POOL = (
    [_p_code_decl] * 24 + [_p_code_if] * 20 + [_p_code_call] * 22 +
    [_p_code_loop] * 14 + [_p_code_comment] * 12
)


# ══════════════════════════════════════════════════════════════════════════════
# STYLE: finance  (trading desk / market data / quant systems)
# ══════════════════════════════════════════════════════════════════════════════

_F_TICKERS   = ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","JPM","GS",
                "MS","BAC","C","WFC","BRK.B","XOM","CVX","UNH","LLY","JNJ",
                "SPX","NDX","DJI","VIX","DXY","EURUSD","USDJPY","GBPUSD",
                "XAUUSD","XAGUSD","BTC","ETH","CL1","NG1","ZB1","ZN1","ES1"]
_F_EXCHANGES = ["NYSE","NASDAQ","LSE","TSE","HKEX","SGX","CME","CBOE","ICE",
                "EUREX","ASX","B3","NSE","MOEX","XETRA","BATS","ARCA","IEX"]
_F_ACTIONS   = ["EXECUTING","ROUTING","MATCHING","CROSSING","HEDGING",
                "ARBITRAGING","REBALANCING","LIQUIDATING","ACCUMULATING",
                "UNWINDING","MARKING","PRICING","SETTLING","CLEARING",
                "ALLOCATING","RISK-CHECKING","MARGINING","REPORTING",
                "RECONCILING","COMPRESSING","ROLLING","SQUARING"]
_F_ORDER_T   = ["MKT","LMT","STP","STP-LMT","MOC","LOC","TWAP","VWAP",
                "ICEBERG","IOC","FOK","GTC","AON","PEG","TRAIL","SNIPER"]
_F_STATUSES  = ["FILLED","PARTIAL","REJECTED","CANCELLED","PENDING","ROUTED",
                "QUEUED","ACK","NACK","TIMEOUT","HALTED","SUSPENDED","LIVE",
                "EXPIRED","TRIGGERED","BREACHED","RECALLED","CONFIRMED"]
_F_DESKS     = ["EQ-FLOW","FI-RATES","FX-SPOT","COMM-DERIV","VOL-ARB",
                "STAT-ARB","INDEX-ARB","DELTA-ONE","PRIME-BROK","RISK-MGT",
                "CLEARING","TREASURY","ALT-DATA","QUANT-STRAT","HFT-MM"]
_F_RISK      = ["VAR","CVAR","DELTA","GAMMA","VEGA","THETA","RHO","DV01",
                "CS01","PV01","IR01","BETA","SHARPE","SORTINO","MAX-DD"]

def _f_price():   return f"{random.uniform(1, 9999):.2f}"
def _f_qty():     return random.randint(100, 10_000_000)
def _f_bps():     return f"{random.uniform(-500, 500):.1f}bp"
def _f_pnl():
    v = random.uniform(-5e6, 5e6)
    return f"{'+'if v>=0 else ''}{v:,.0f}"
def _f_orderid(): return f"ORD-{random.randint(100000000,999999999)}"

def _f_line_trade():
    ticker = random.choice(_F_TICKERS)
    side   = random.choice(["BUY ","SELL"])
    qty    = _f_qty()
    px     = _f_price()
    exch   = random.choice(_F_EXCHANGES)
    otype  = random.choice(_F_ORDER_T)
    return (f"[{TIMESTAMP()}] {side} {qty:>10,d} {ticker:<7s}"
            f"  @ {px:>9s}  {otype:<8s} {exch:<6s}  {random.choice(_F_STATUSES)}")

def _f_line_risk():
    desk   = random.choice(_F_DESKS)
    metric = random.choice(_F_RISK)
    val    = random.uniform(-1e7, 1e7)
    limit  = abs(val) * random.uniform(1.0, 3.0)
    pct    = abs(val) / limit * 100
    flag   = "  !" if pct > 85 else "   "
    return (f"  {desk:<14s}  {metric:<7s}  {val:>+12,.0f}"
            f"  lim {limit:>10,.0f}  {pct:5.1f}%{flag}")

def _f_line_quote():
    ticker = random.choice(_F_TICKERS)
    bid    = random.uniform(1, 9999)
    spd    = random.uniform(0.01, 2.0)
    ask    = bid + spd
    chg    = random.uniform(-5, 5)
    vol    = random.randint(1000, 50_000_000)
    return (f"  {ticker:<7s}  bid {bid:>9.2f}  ask {ask:>9.2f}"
            f"  chg {chg:>+6.2f}  vol {vol:>12,d}")

def _f_line_action():
    return (f"[{TIMESTAMP()}] {random.choice(_F_ACTIONS)}"
            f" {random.choice(_F_TICKERS)} {random.choice(_F_ORDER_T)}"
            f" ... {random.choice(_F_STATUSES)}")

def _f_line_pnl():
    desk = random.choice(_F_DESKS)
    d_pnl = _f_pnl()
    ytd   = _f_pnl()
    return f"  PNL  {desk:<14s}  daily {d_pnl:>12s}  YTD {ytd:>14s}"

def _f_line_order():
    return (f"  {_f_orderid()}  {random.choice(_F_TICKERS):<7s}"
            f"  {random.choice(['BUY ','SELL'])} {_f_qty():>10,d}"
            f"  {_f_price():>9s}  {random.choice(_F_STATUSES)}")

def _f_line_matrix():
    # Correlation matrix row
    vals = "  ".join(f"{random.uniform(-1,1):+.3f}" for _ in range(7))
    return f"  corr  [{vals}]"

def _f_line_alert():
    codes = ["CIRCUIT-BREAKER","MARGIN-CALL","POSITION-LIMIT","LOSS-LIMIT",
             "RATE-LIMIT","FEED-STALE","LATENCY-SPIKE","KILL-SWITCH",
             "RECON-BREAK","SETTLEMENT-FAIL","SHORT-SQUEEZE","HALT"]
    return (f"!! {random.choice(codes)}  {random.choice(_F_TICKERS)}"
            f"  {random.choice(_F_DESKS)}  t={TIMESTAMP()}")

def _f_rcol_ticker():
    chg = random.uniform(-10, 10)
    return f"{random.choice(_F_TICKERS):<7s} {chg:>+7.2f}%"
def _f_rcol_price():
    return f"{random.choice(_F_TICKERS):<7s} {_f_price():>9s}"
def _f_rcol_status():
    return f"{random.choice(_F_STATUSES):>14s}"
def _f_rcol_pnl():
    return f"PNL {_f_pnl():>12s}"
def _f_rcol_risk():
    return f"{random.choice(_F_RISK):<7s} {random.uniform(-1e6,1e6):>+12,.0f}"
def _f_rcol_bps():
    return f"{random.choice(_F_TICKERS):<7s} {_f_bps():>9s}"

_F_GENERATORS = [
    (_f_line_trade,   22), (_f_line_quote,   18), (_f_line_action,  14),
    (_f_line_risk,    12), (_f_line_pnl,     10), (_f_line_order,   10),
    (_f_line_matrix,   8), (_f_line_alert,    6),
]
_F_RCOL_POOL = (
    [_f_rcol_ticker]*25 + [_f_rcol_price]*20 + [_f_rcol_status]*15 +
    [_f_rcol_pnl]*15    + [_f_rcol_risk]*15   + [_f_rcol_bps]*10
)


# ══════════════════════════════════════════════════════════════════════════════
# STYLE: space  (deep-space mission operations / spacecraft telemetry)
# ══════════════════════════════════════════════════════════════════════════════

_SP_VESSELS   = ["ODYSSEY-1","ARES-IV","HERMES","ENDURANCE","DISCOVERY",
                 "PROMETHEUS","NOSTROMO","ELYSIUM","PIONEER-12","VOYAGER-3",
                 "ARTEMIS-7","COLUMBIA-II","INTREPID","HORIZON-9","SOLARIS"]
_SP_SYSTEMS   = ["RCS","ECLSS","OMS","GNC","EPS","TCS","PROP","COMMS",
                 "AOCS","ADCS","CDH","PYRO","FDIR","IDS","TDRSS-LINK"]
_SP_ACTIONS   = ["NOMINAL","CALIBRATING","INITIALIZING","EXECUTING","TRACKING",
                 "ACQUIRING","DOWNLINKING","UPLINK-CONFIRM","BURN-COMPLETE",
                 "CONTINGENCY","ANOMALY","SAFING","RECONFIGURING","VENTING",
                 "PRESSURIZING","DEPLOYING","SEPARATING","DOCKING","EJECTING"]
_SP_SUBSYS    = ["main engine","RCS thruster","solar array","fuel cell",
                 "reaction wheel","star tracker","inertial nav","comms antenna",
                 "thermal radiator","cryo tank","battery pack","CPU-A","CPU-B",
                 "attitude sensor","docking port","airlock seal","EVA suit"]
_SP_STATUSES  = ["NOMINAL","GO","NO-GO","STANDBY","ACTIVE","FAULT","INHIBIT",
                 "OVERRIDE","TIMEOUT","LOST-SIGNAL","REACQUIRED","CONTINGENCY",
                 "RED-LINE","CAUTION","WARNING","EMERGENCY","RECOVERY","SAFE"]
_SP_PLANETS   = ["Earth","Mars","Moon","Europa","Titan","Enceladus",
                 "Ceres","Ganymede","Callisto","asteroid belt"]
_SP_MISSION_T = ["MET","GMT","UTC","EST","TIG","EI","PDI","TLI","LOI","TEI"]

_sp_dist  = lambda: f"{random.uniform(0, 4e8):.3e} km"
_sp_vel   = lambda: f"{random.uniform(0.1, 30.0):.3f} km/s"
_sp_temp  = lambda: f"{random.uniform(-270, 1500):.1f} K"
_sp_angle = lambda: f"{random.uniform(0, 360):.4f} deg"
_sp_pct   = lambda: f"{random.uniform(0, 100):.1f}%"
_sp_met   = lambda: (f"MET +{random.randint(0,999):03d}:"
                     f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:"
                     f"{random.randint(0,59):02d}")

def _sp_line_telemetry():
    sys = random.choice(_SP_SYSTEMS)
    return (f"[{_sp_met()}] {sys:<6s}  {random.choice(_SP_SUBSYS):<20s}"
            f"  {random.choice(_SP_ACTIONS):<16s}  {random.choice(_SP_STATUSES)}")

def _sp_line_nav():
    body = random.choice(_SP_PLANETS)
    return (f"  NAV  range={_sp_dist():<16s}  vel={_sp_vel():<12s}"
            f"  body={body:<10s}  az={_sp_angle()}")

def _sp_line_burn():
    dv   = random.uniform(0.1, 500)
    dur  = random.uniform(1, 3600)
    pct  = random.uniform(85, 102)
    return (f"  BURN  dV={dv:7.2f} m/s  dur={dur:7.1f}s"
            f"  thrust={pct:.1f}%  {random.choice(_SP_STATUSES)}")

def _sp_line_power():
    gen  = random.uniform(0, 20000)
    cons = random.uniform(0, 20000)
    batt = random.uniform(0, 100)
    return (f"  EPS  gen={gen:8.1f}W  cons={cons:8.1f}W"
            f"  batt={batt:.1f}%  {random.choice(_SP_STATUSES)}")

def _sp_line_thermal():
    comp = random.choice(_SP_SUBSYS)
    return (f"  TCS  {comp:<22s}  T={_sp_temp():<10s}"
            f"  limit={_sp_temp():<10s}  {random.choice(_SP_STATUSES)}")

def _sp_line_comms():
    rate  = random.uniform(0.01, 10000)
    snr   = random.uniform(-5, 40)
    light = random.uniform(0.001, 22)
    return (f"  COMMS  rate={rate:8.2f} bps  SNR={snr:+5.1f}dB"
            f"  light-time={light:.3f}min  {random.choice(_SP_STATUSES)}")

def _sp_line_crew():
    names  = ["CDR HAYES","PLT CHEN","MS1 OKAFOR","MS2 PETROV",
              "PS1 YAMAMOTO","FE DIAZ","EV1 SINGH","EV2 LARSSON"]
    vitals = ["HR","SpO2","SUIT-P","O2-FLOW","CO2","TEMP"]
    name   = random.choice(names)
    vital  = random.choice(vitals)
    val    = random.uniform(0, 200)
    return (f"  CREW  {name:<16s}  {vital:<8s}  {val:6.1f}"
            f"  {random.choice(_SP_STATUSES)}")

def _sp_line_alert():
    codes = ["MASTER-ALARM","SEP-FAULT","PRESS-LOSS","ABORT-GUIDANCE",
             "THRUSTER-LEAK","COMM-BLACKOUT","ATTITUDE-ERR","POWER-FAIL",
             "METEOROID-HIT","RADIATION-DOSE","EVA-ABORT","DOCKING-FAIL"]
    return (f"!! {random.choice(codes)}  {random.choice(_SP_SYSTEMS)}"
            f"  {_sp_met()}  {random.choice(_SP_STATUSES)}")

def _sp_line_matrix():
    row = "  ".join(f"{random.gauss(0,1):+.4f}" for _ in range(6))
    return f"  ATT-MATRIX  [{row}]"

def _sp_rcol_sys():
    return f"{random.choice(_SP_SYSTEMS):<6s}  {random.choice(_SP_STATUSES)}"
def _sp_rcol_val():
    labels = ["ALT","VEL","TEMP","PWR","BATT","SNR","dV","PRES"]
    return f"{random.choice(labels):<5s} {random.uniform(-999,9999):>9.2f}"
def _sp_rcol_met():
    return _sp_met()
def _sp_rcol_vessel():
    return random.choice(_SP_VESSELS)
def _sp_rcol_angle():
    return f"AZ={_sp_angle()}"
def _sp_rcol_status():
    return f"{random.choice(_SP_STATUSES):>14s}"

_SP_GENERATORS = [
    (_sp_line_telemetry, 22), (_sp_line_nav,    16), (_sp_line_burn,    12),
    (_sp_line_power,     12), (_sp_line_thermal, 10), (_sp_line_comms,   10),
    (_sp_line_crew,       8), (_sp_line_alert,   6), (_sp_line_matrix,   4),
]
_SP_RCOL_POOL = (
    [_sp_rcol_sys]*25    + [_sp_rcol_val]*20  + [_sp_rcol_met]*15 +
    [_sp_rcol_vessel]*15 + [_sp_rcol_angle]*15 + [_sp_rcol_status]*10
)

# ══════════════════════════════════════════════════════════════════════════════
# STYLE: military  (tactical command / battlefield / intel)
# ══════════════════════════════════════════════════════════════════════════════

_MI_UNITS     = ["ALPHA-1","BRAVO-2","CHARLIE-3","DELTA-4","ECHO-5",
                 "FOXTROT-6","GHOST-7","HAMMER-8","IRON-9","JULIET-10",
                 "KILO-11","LIGHTNING-12","NOMAD-13","ORACLE-14","PHANTOM-15"]
_MI_PLATFORMS = ["F-35A","F-22","B-2","AC-130","MQ-9","RQ-4","AH-64",
                 "M1A2","CV-90","M270","AEGIS-CG","DDG-109","SSN-774",
                 "V-22","CH-47","UH-60","E-8C","RC-135","EC-130"]
_MI_ACTIONS   = ["ENGAGING","TRACKING","ACQUIRING","SUPPRESSING","ADVANCING",
                 "WITHDRAWING","HOLDING","FLANKING","BREACHING","ESTABLISHING",
                 "DESTROYING","NEUTRALIZING","RELOCATING","EXTRACTING",
                 "CONFIRMING","DENYING","JAMMING","INTERCEPT","OBSERVING"]
_MI_GRID      = lambda: (f"{random.randint(10,99)}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}"
                         f"{random.randint(100,999)}{random.randint(100,999)}")
_MI_BEARING   = lambda: f"{random.randint(0,359):03d}"
_MI_RANGE_    = lambda: f"{random.uniform(0.1, 50.0):.1f}km"
_MI_SPEED_    = lambda: f"{random.randint(0, 900)}kph"
_MI_ALT       = lambda: f"{random.randint(0, 50000)}ft"
_MI_FREQS     = ["HAVE-QUICK","SATURN-V","SINCGARS","LINK-16","TADIL-J",
                 "UHF-SAT","MILSTAR","JTIDS","IFF-MODE4","CRYPTO-KY58"]
_MI_THREATS   = ["MANPAD","AAA","SAM-SA8","SAM-S400","MBT","IFV","APC",
                 "RADAR-TRACK","EW-JAMMING","CYBER-INTRUSION","DRONE-SWARM"]
_MI_STATUSES  = ["WEAPONS-FREE","WEAPONS-HOLD","WEAPONS-TIGHT","KIA","WIA",
                 "BINGO-FUEL","WINCHESTER","RTB","SPLASH","GOOD-HITS",
                 "CLEAN","NEGATIVE","CONFIRM","DENY","STANDBY","EXECUTE",
                 "ABORT","WINCHESTER","NO-JOY","TALLY","VISUAL","BLIND"]
_MI_CLASSIF   = ["UNCLASSIFIED","CONFIDENTIAL","SECRET","TOP SECRET","SCI"]

def _mi_line_contact():
    return (f"[{TIMESTAMP()}] CONTACT  {random.choice(_MI_THREATS):<14s}"
            f"  GRID {_MI_GRID()}  BRG {_MI_BEARING()}  RNG {_MI_RANGE_()}"
            f"  {random.choice(_MI_STATUSES)}")

def _mi_line_unit():
    unit   = random.choice(_MI_UNITS)
    action = random.choice(_MI_ACTIONS)
    return (f"[{TIMESTAMP()}] {unit:<12s}  {action:<14s}"
            f"  GRID {_MI_GRID()}  {random.choice(_MI_STATUSES)}")

def _mi_line_air():
    ac  = random.choice(_MI_PLATFORMS)
    return (f"  AIRTRACK  {ac:<8s}  ALT {_MI_ALT():<8s}"
            f"  HDG {_MI_BEARING()}  SPD {_MI_SPEED_():<8s}"
            f"  {random.choice(_MI_STATUSES)}")

def _mi_line_fire():
    wpn  = random.choice(["HELLFIRE","JDAM","HARM","AIM-120","M829A3",
                          "JAVELIN","SPIKE","HYDRA-70","30MM","120MM-SABOT"])
    tgt  = _MI_GRID()
    return (f"  FIRE-MISSION  {wpn:<12s}  TGT-GRID {tgt}"
            f"  {random.choice(_MI_STATUSES)}")

def _mi_line_sigint():
    freq = f"{random.uniform(30, 3000):.3f}MHz"
    src  = _MI_GRID()
    return (f"  SIGINT  FREQ {freq:<12s}  GRID {src}"
            f"  NET {random.choice(_MI_FREQS):<12s}  {random.choice(_MI_STATUSES)}")

def _mi_line_logistics():
    item = random.choice(["FUEL","AMMO-5.56","AMMO-7.62","120MM","JAVELIN",
                          "BATTERY-BA5590","WATER","RATIONS","MEDEVAC","CAS"])
    qty  = random.randint(1, 9999)
    return (f"  LOG  {item:<16s}  QTY {qty:>6d}"
            f"  GRID {_MI_GRID()}  {random.choice(_MI_STATUSES)}")

def _mi_line_intel():
    classif = random.choice(_MI_CLASSIF)
    return (f"  INTEL//{classif}  {random.choice(_MI_ACTIONS)} {random.choice(_MI_THREATS)}"
            f"  CONF {random.randint(10,99)}%  GRID {_MI_GRID()}")

def _mi_line_comms():
    net  = random.choice(_MI_FREQS)
    return (f"  COMMS  NET {net:<14s}  {random.choice(_MI_UNITS)}"
            f"  {random.choice(_MI_ACTIONS)[:12]}  {random.choice(_MI_STATUSES)}")

def _mi_line_alert():
    codes = ["TROOPS-IN-CONTACT","MASS-CAS","NBC-ALERT","MEDEVAC-REQUEST",
             "BINGO-FUEL","WINCHESTER","EW-DETECTED","CYBER-BREACH",
             "BLUE-ON-BLUE","ABORT-ABORT","CEASE-FIRE","FLASH-TRAFFIC"]
    return (f"!! {random.choice(codes)}  {random.choice(_MI_UNITS)}"
            f"  GRID {_MI_GRID()}  t={TIMESTAMP()}")

def _mi_rcol_unit():
    return f"{random.choice(_MI_UNITS):<12s} {random.choice(_MI_STATUSES)}"
def _mi_rcol_grid():
    return f"GRID {_MI_GRID()}"
def _mi_rcol_platform():
    return f"{random.choice(_MI_PLATFORMS):<8s} {_MI_ALT()}"
def _mi_rcol_status():
    return f"{random.choice(_MI_STATUSES):>14s}"
def _mi_rcol_brg():
    return f"BRG {_MI_BEARING()}  RNG {_MI_RANGE_()}"

_MI_GENERATORS = [
    (_mi_line_contact,   20), (_mi_line_unit,      18), (_mi_line_air,       14),
    (_mi_line_fire,      10), (_mi_line_sigint,     10), (_mi_line_logistics,  8),
    (_mi_line_intel,      8), (_mi_line_comms,       8), (_mi_line_alert,      4),
]
_MI_RCOL_POOL = (
    [_mi_rcol_unit]*25   + [_mi_rcol_grid]*20   + [_mi_rcol_platform]*20 +
    [_mi_rcol_status]*20 + [_mi_rcol_brg]*15
)

# ══════════════════════════════════════════════════════════════════════════════
# STYLE: navigation  (satnav / autonomous vehicle / real-time routing)
# ══════════════════════════════════════════════════════════════════════════════

_NAV_ROADS    = ["M25","A316","Route 66","I-405","N1","B4040","Ring Road",
                 "Central Expressway","Harbor Freeway","Eastern Bypass",
                 "Orbital Route","Highway 101","Autobahn A9","Via Appia"]
_NAV_PLACES   = ["Heathrow Terminal 5","City Centre","Airport Junction",
                 "Waterfront District","University Campus","Industrial Park",
                 "Shopping Centre","Hospital","Train Station","Ferry Terminal",
                 "Sports Stadium","Convention Centre","Old Town","Tech Quarter"]
_NAV_MANEUV   = ["TURN LEFT","TURN RIGHT","BEAR LEFT","BEAR RIGHT","KEEP LEFT",
                 "KEEP RIGHT","MERGE","TAKE EXIT","CONTINUE STRAIGHT","U-TURN",
                 "ROUNDABOUT 2ND EXIT","ROUNDABOUT 3RD EXIT","STAY ON",
                 "FOLLOW SIGNS FOR","ENTER MOTORWAY","LEAVE MOTORWAY"]
_NAV_UNITS_D  = ["m","km","yd","mi","ft"]
_NAV_STREETS  = ["High Street","Church Road","Station Road","Park Avenue",
                 "Victoria Street","King's Road","Queens Way","Bridge Street",
                 "Market Street","The Broadway","North Circular","South Ring",
                 "Commercial Road","Harbour Drive","Riverside Walk"]

# Right-column alert pools — urgent, medium, ambient
_NAV_ALERTS_URGENT = [
    "!! COLLISION AHEAD",
    "!! EMERGENCY VEHICLE",
    "!! ROAD CLOSED",
    "!! ACCIDENT - 2 LANES BLOCKED",
    "!! PEDESTRIAN IN ROAD",
    "!! ICE WARNING",
    "!! SCHOOL ZONE ACTIVE",
    "!! BRIDGE WEIGHT LIMIT",
    "!! LEVEL CROSSING AHEAD",
    "!! EMERGENCY BRAKING AHEAD",
]
_NAV_ALERTS_MED = [
    "HEAVY TRAFFIC AHEAD",
    "STOP LIGHT - 400m",
    "SPEED CAMERA - 300m",
    "PEDESTRIAN CROSSING",
    "CYCLIST AHEAD",
    "ROADWORKS - REDUCE SPEED",
    "MERGING TRAFFIC",
    "NARROW LANE AHEAD",
    "LOW BRIDGE - 4.2m",
    "SHARP BEND AHEAD",
    "RAILWAY CROSSING",
    "ANIMAL CROSSING ZONE",
    "CHILDREN CROSSING",
]
_NAV_ALERTS_AMBIENT = [
    "Recalculating route...",
    "GPS signal strong",
    "ETA updating",
    "Traffic data refreshed",
    "Toll road ahead",
    "Fuel station in 2km",
    "Rest area in 5km",
    "Speed limit: 50km/h",
    "Speed limit: 30km/h",
    "Night mode active",
    "Lane assist ON",
    "Cruise control set",
    "Parking ahead",
    "Charging point 800m",
]

def _nav_dist():
    d = random.choice([
        f"{random.randint(10,999)}m",
        f"{random.uniform(0.1, 50.0):.1f}km",
        f"{random.randint(100,1000)}ft",
        f"{random.uniform(0.1, 30.0):.1f}mi",
    ])
    return d

def _nav_eta():
    h = random.randint(0, 4)
    m = random.randint(0, 59)
    if h:
        return f"{h}h {m:02d}min"
    return f"{m}min"

def _nav_line_maneuver():
    m    = random.choice(_NAV_MANEUV)
    dist = _nav_dist()
    road = random.choice(_NAV_STREETS)
    return f"  {m:<26s}  onto {road:<20s}  in {dist}"

def _nav_line_routing():
    dest = random.choice(_NAV_PLACES)
    eta  = _nav_eta()
    dist = _nav_dist()
    spd  = random.randint(20, 120)
    return (f"[{TIMESTAMP()}]  DEST: {dest:<26s}"
            f"  ETA {eta:<9s}  {dist:<8s}  {spd}km/h")

def _nav_line_traffic():
    road  = random.choice(_NAV_ROADS)
    delay = random.randint(1, 45)
    dist  = _nav_dist()
    cond  = random.choice(["HEAVY","SLOW","MODERATE","QUEUING","STATIONARY",
                           "MOVING","LIGHT","CLEAR","UNKNOWN"])
    return (f"  TRAFFIC  {road:<16s}  {cond:<12s}"
            f"  +{delay}min delay  {dist} ahead")

def _nav_line_gps():
    lat  = random.uniform(-90, 90)
    lon  = random.uniform(-180, 180)
    acc  = random.uniform(1, 20)
    sats = random.randint(4, 18)
    return (f"  GPS  lat={lat:>+10.6f}  lon={lon:>+11.6f}"
            f"  acc={acc:.1f}m  sats={sats}")

def _nav_line_sensor():
    sensors = ["LIDAR-F","LIDAR-R","RADAR-F","RADAR-L","RADAR-R",
               "CAM-360","ULTRASONIC-F","ULTRASONIC-R","IMU","ODOMETER"]
    s    = random.choice(sensors)
    val  = random.uniform(0, 200)
    unit = random.choice(["m","km/h","deg","Hz","fps"])
    return (f"  SENSOR  {s:<14s}  {val:8.2f} {unit:<5s}"
            f"  {random.choice(['OK','NOMINAL','DEGRADED','FAULT'])}")

def _nav_line_reroute():
    via  = random.choice(_NAV_ROADS)
    save = random.randint(1, 30)
    dist = _nav_dist()
    return (f"  REROUTE  via {via:<16s}  saves {save}min"
            f"  alt-dist {dist}  {random.choice(['FASTER','SHORTER','SCENIC','TOLL-FREE'])}")

def _nav_line_hazard():
    return (f"  HAZARD  {random.choice(_NAV_ALERTS_URGENT + _NAV_ALERTS_MED)}"
            f"  dist={_nav_dist()}  t={TIMESTAMP()}")

def _nav_line_alert_lh():
    """Occasional full-line alert on the left side too."""
    return (f"!! {random.choice(_NAV_ALERTS_URGENT)}"
            f"  {_nav_dist()}  t={TIMESTAMP()}")

# Right-column: mix of urgent (rare), medium (common), ambient (majority)
def _nav_rcol_alert():
    roll = random.random()
    if roll < 0.12:
        return random.choice(_NAV_ALERTS_URGENT)
    elif roll < 0.50:
        return random.choice(_NAV_ALERTS_MED)
    else:
        return random.choice(_NAV_ALERTS_AMBIENT)

def _nav_rcol_eta():
    dest = random.choice(_NAV_PLACES)[:16]
    return f"{dest:<16s} {_nav_eta()}"

def _nav_rcol_speed():
    return f"SPEED  {random.randint(0,130):>3d} km/h"

def _nav_rcol_sat():
    return f"SAT {random.randint(4,18):>2d}  ACC {random.uniform(1,15):.1f}m"

_NAV_GENERATORS = [
    (_nav_line_maneuver,  24), (_nav_line_routing,   20), (_nav_line_traffic,   16),
    (_nav_line_gps,       12), (_nav_line_sensor,    10), (_nav_line_reroute,    8),
    (_nav_line_hazard,     6), (_nav_line_alert_lh,   4),
]
# Right column: mostly alert text, heavier blank probability handled upstream
_NAV_RCOL_POOL = (
    [_nav_rcol_alert]*50 + [_nav_rcol_eta]*20 +
    [_nav_rcol_speed]*15 + [_nav_rcol_sat]*15
)


# ══════════════════════════════════════════════════════════════════════════════
# STYLE: spaceteam  (cooperative technobabble chaos)
# ══════════════════════════════════════════════════════════════════════════════

# ── Morpheme pools for compound instrument names ──────────────────────────────
_ST_PRE1 = ["CHRONO","QUANTUM","TURBO","HYPER","MEGA","ULTRA","PROTO","ASTRO",
            "PLASMA","FUSION","VORTEX","STELLAR","WARP","FLUX","NANO","DARK",
            "ANTI","INTER","OMNI","POLY","PSEUDO","RETRO","TRANS","SONIC",
            "HYDRO","THERMO","NEURO","CYBER","PHOTON","TACHYON","TORSION",
            "SUBSPACE","INVERSE","LATERAL","BINARY","HELIO","GRAV","CRYO",
            "BIONIC","MUON","QUARK","PULSAR","NEBULA","COSMO","PENTA"]

_ST_PRE2 = ["FLUX","BRINE","PHASE","WAVE","PULSE","BOOST","DRIVE","CORE",
            "BEAM","FIELD","LOCK","PORT","GRID","SCAN","LOOP","BANK",
            "BURST","SURGE","SPIN","LINK","NODE","RING","ZONE","PIPE",
            "VENT","GATE","DOME","LENS","COIL","PLATE","TANK","CELL",
            "DIAL","BLORP","FRING","GLORP","ZORP","WUMBLE","SNORKEL",
            "SPROCKET","GASKET","DOINK","THRUMBLE","FLORP","BINGLE"]

_ST_NOUN = ["STABILIZER","MODULATOR","INVERTER","CAPACITOR","COMPENSATOR",
            "OSCILLATOR","REGULATOR","ATTENUATOR","AMPLIFIER","CONVERTER",
            "ACCELERATOR","TRANSDUCER","RESONATOR","EMITTER","DEFLECTOR",
            "EXTRACTOR","INJECTOR","SUPPRESSOR","GENERATOR","ACTUATOR",
            "ENCABULATOR","DECOUPLER","CONDENSER","DISRUPTOR","HARMONIZER",
            "REALIGNER","CALIBRATOR","BIFURCATOR","DOOHICKEY","THINGAMAJIG",
            "WHATSIT","CONTRAPTION","GIZMO","WIDGET","DOODAD","APPARATUS",
            "RECOMBOBULATOR","DISCOMBOBULATOR","FLIBBERTIGIBBET","OSCILLOGRAPH",
            "PERAMBULATOR","REVERBERATOR","DESTABILIZER","AMALGAMATOR",
            "DECOMPLEXIFIER","HYPERDRIVE","TRANSMOGRIFIER","REPULSORLIFT"]

# ── Made-up units ─────────────────────────────────────────────────────────────
_ST_UNITS = ["GLORPS","WUMBLES","MILLIFARPS","ZEPTOSIEVERTS","FLURBS",
             "BLORPS","QUIBITS","SNARGS","WUBBLES","FRINDLES","DOINKS",
             "MEGA-SNORPS","THRUMBLES","GLORBLES","ZORGAWATTS","SPLURTS",
             "CROMULENT UNITS","BIBBLES","MICRO-DARGS","FWUMPS","GAZORPS",
             "SCHMIBBLES","KLAXONS","BINGLE-HERTZ","FLANGE-PASCALS"]

# ── Imperative verbs ──────────────────────────────────────────────────────────
_ST_VERBS = ["SET","ENGAGE","DISENGAGE","ACTIVATE","DEACTIVATE","BOOST",
             "REDUCE","CALIBRATE","RECALIBRATE","REVERSE","TOGGLE","PURGE",
             "VENT","PRIME","INITIALIZE","OVERRIDE","BYPASS","AMPLIFY",
             "INVERT","OSCILLATE","MODULATE","FLUX","DISCHARGE","RECHARGE",
             "JIGGLE","WIGGLE","SMACK","THUMP","ROTATE","WOBBLE","NUDGE",
             "MAXIMISE","MINIMISE","TRIANGULATE","DISCOMBOBULATE","YEET"]

# ── Status / readout words ─────────────────────────────────────────────────────
_ST_STATES = ["NOMINAL","STABLE","ENGAGED","ACTIVE","STANDBY","OPTIMAL",
              "OVERLOADING","CRITICAL","CATASTROPHIC","BZZZT","NOMINAL",
              "WOBBLING","SPLORTING","FRIBBLING","???","NOMINAL","ENGAGED",
              "VERY YES","DEFINITELY NO","MAYBE","PLEASE STOP","NOMINAL",
              "ON FIRE (METAPHORICALLY)","TECHNICALLY FINE","¯\\_(ツ)_/¯",
              "NOMINAL","BOOSTING","MAXIMUM OVERDRIVE","VIBRATING STRONGLY"]

# ── Panels / locations ────────────────────────────────────────────────────────
_ST_PANELS = ["PANEL A","PANEL B","PANEL C","PANEL D","STATION 1","STATION 2",
              "UPPER DECK","LOWER DECK","AFT SECTION","BOW SECTION","PORT SIDE",
              "STARBOARD","ENGINEERING","BRIDGE","CARGO BAY","AIRLOCK SEVEN"]

# ── The occasional embarrassingly mundane instruction ─────────────────────────
_ST_MUNDANE = [
    "CHECK OIL LEVEL",
    "HAVE YOU TRIED TURNING IT OFF AND ON AGAIN?",
    "FASTEN SEATBELT",
    "MIND THE GAP",
    "PLEASE HOLD",
    "WIPE YOUR FEET",
    "DID YOU SAVE YOUR PROGRESS?",
    "LOW PRINTER INK",
    "DISHWASHER CYCLE COMPLETE",
    "YOUR PACKAGE HAS BEEN DELIVERED",
    "SOFTWARE UPDATE AVAILABLE",
    "BATTERY LOW",
    "REMINDER: HYDRATE",
]

# ── Helper: generate a random instrument name ─────────────────────────────────
def _st_instrument():
    style = random.randint(0, 3)
    if style == 0:
        return f"{random.choice(_ST_PRE1)}-{random.choice(_ST_NOUN)}"
    elif style == 1:
        return f"{random.choice(_ST_PRE1)} {random.choice(_ST_PRE2)} {random.choice(_ST_NOUN)}"
    elif style == 2:
        return f"{random.choice(_ST_PRE1)}{random.choice(_ST_PRE2)} {random.choice(_ST_NOUN)}"
    else:
        return f"{random.choice(_ST_PRE2)}-{random.choice(_ST_PRE1)} {random.choice(_ST_NOUN)}"

def _st_value():
    """A dial value: integer, decimal, roman numeral, or word."""
    r = random.random()
    if r < 0.35:
        return str(random.randint(0, 11))
    elif r < 0.55:
        return f"{random.uniform(0, 9.9):.1f}"
    elif r < 0.70:
        return random.choice(["I","II","III","IV","V","VI","VII","VIII","IX","X","XI"])
    elif r < 0.82:
        return random.choice(["MIN","MAX","OFF","ON","LOW","HIGH","MEDIUM","FULL","ZERO","ELEVEN"])
    else:
        return f"{random.randint(100, 9999)}"

# ── Left-column line generators ───────────────────────────────────────────────

def _st_line_instruction():
    """The core Spaceteam mechanic: imperative command."""
    verb = random.choice(_ST_VERBS)
    inst = _st_instrument()
    val  = _st_value()
    # Sometimes "SET X TO N", sometimes just "ACTIVATE X", sometimes with urgency
    urgency = random.random()
    if verb in ("SET","BOOST","REDUCE","AMPLIFY","MAXIMISE","MINIMISE"):
        base = f"{verb} {inst} TO {val}"
    else:
        base = f"{verb} THE {inst}"
    if urgency > 0.85:
        base = base + "  !!!"
    elif urgency > 0.72:
        base = base + "  !!"
    elif urgency > 0.60:
        base = base + "  !"
    return f"  {base}"

def _st_line_readout():
    """Panel instrument readout showing current value."""
    inst = _st_instrument()
    val  = _st_value()
    unit = random.choice(_ST_UNITS)
    state = random.choice(_ST_STATES)
    return f"  {inst:<36s}  {val:>6s} {unit:<18s}  [{state}]"

def _st_line_warning():
    """Escalating warning message."""
    inst  = _st_instrument()
    level = random.choice(["NOTICE","CAUTION","WARNING","ALARM","CRITICAL",
                           "DANGER","CATASTROPHIC FAILURE","OH NO","VERY BAD",
                           "EXTREMELY CONCERNING","PLEASE PANIC","YIKES"])
    return f"  {level}: {inst} OUT OF NOMINAL PARAMETERS"

def _st_line_comms():
    """Crew cross-talk."""
    names  = ["CAPTAIN","HELMSMAN","ENGINEER","SCIENCE OFFICER","COOK",
              "INTERN","GARY","THE ROBOT","SOMEONE","UNKNOWN CREW MEMBER"]
    sender = random.choice(names)
    recvr  = random.choice(names)
    inst   = _st_instrument()
    verb   = random.choice(_ST_VERBS)
    return f"  [{sender}] -> [{recvr}]: PLEASE {verb} THE {inst}"

def _st_line_countdown():
    """Timed event countdown."""
    event = random.choice(["SELF-DESTRUCT","HYPERSPACE JUMP","CORE PURGE",
                           "MANDATORY REBOOT","SURPRISE","COFFEE BREAK",
                           "SCHEDULED PANIC","WARP BUBBLE COLLAPSE",
                           "SNACK TIME","ALIEN CONTACT","IMPLOSION"])
    secs  = random.randint(3, 999)
    return f"  COUNTDOWN: {event:<30s}  T-{secs:03d}s"

def _st_line_diagnostic():
    """System diagnostic result."""
    inst   = _st_instrument()
    result = random.choice(["PASS","FAIL","PASS","PASS","FAIL","INDETERMINATE",
                            "SURPRISINGLY OK","WORSE THAN EXPECTED","FINE I GUESS",
                            "DO NOT LOOK AT IT","PASS","HMMMM"])
    pct    = random.randint(0, 100)
    return f"  DIAG  {inst:<36s}  {pct:>3d}%  {result}"

def _st_line_mundane():
    """Completely out-of-place mundane system message."""
    return f"  *** SYSTEM ALERT: {random.choice(_ST_MUNDANE)} ***"

def _st_line_gibberish():
    """Pure technobabble stream — things are getting bad."""
    words = [random.choice(_ST_PRE1 + _ST_PRE2) for _ in range(random.randint(4,8))]
    return "  " + " ".join(words) + " " + random.choice(_ST_NOUN) + "!!!!"

def _st_line_alert():
    """Red-level crisis line."""
    inst = _st_instrument()
    codes = ["CONTAINMENT BREACH","CORE MELTDOWN","HULL INTEGRITY CRITICAL",
             "SHIELDS AT ZERO","ENGINES OFFLINE","WE'RE ALL GONNA DIE",
             "TEMPORAL PARADOX","UNEXPECTED TROMBONE","GRAVITY REVERSED",
             "COFFEE MACHINE OFFLINE","CREW TURNED INTO CATS","REALITY UNSTABLE"]
    return f"!! {random.choice(codes)}  [{inst}]  {random.choice(_ST_PANELS)}"

# ── Right-column: panel gauge readouts ───────────────────────────────────────

def _st_rcol_gauge():
    inst  = _st_instrument().split()[0][:12]   # just the first word, truncated
    val   = _st_value()
    return f"{inst:<12s} [{val:>6s}]"

def _st_rcol_state():
    return random.choice(_ST_STATES)[:20]

def _st_rcol_unit():
    val  = _st_value()
    unit = random.choice(_ST_UNITS)[:12]
    return f"{val:>6s} {unit}"

def _st_rcol_panel():
    panel = random.choice(_ST_PANELS)
    state = random.choice(["OK","OK","OK","!!","???","BZZZT","FINE"])
    return f"{panel:<14s} {state}"

def _st_rcol_countdown():
    return f"T-{random.randint(0,999):03d}s"

_ST_GENERATORS = [
    (_st_line_instruction,  30),   # the core mechanic — most common
    (_st_line_readout,      20),
    (_st_line_warning,      14),
    (_st_line_comms,        10),
    (_st_line_countdown,     8),
    (_st_line_diagnostic,    8),
    (_st_line_mundane,       5),   # rare mundane = bigger laughs
    (_st_line_gibberish,     3),   # rare pure chaos
    (_st_line_alert,         2),
]
_ST_RCOL_POOL = (
    [_st_rcol_gauge]*30   + [_st_rcol_state]*25  + [_st_rcol_unit]*20 +
    [_st_rcol_panel]*15   + [_st_rcol_countdown]*10
)

# ══════════════════════════════════════════════════════════════════════════════
# Style dispatch — GEN_POOL and RCOL_POOL are filled at startup once --style known
# ══════════════════════════════════════════════════════════════════════════════

def _build_pools(style: str):
    """Return (gen_pool, rcol_pool) for the given style name."""
    if style == "science":
        gens, rcol = _S_GENERATORS, _S_RCOL_POOL
    elif style == "medicine":
        gens, rcol = _M_GENERATORS, _M_RCOL_POOL
    elif style == "pharmacy":
        gens, rcol = _P_GENERATORS, _P_RCOL_POOL
    elif style == "finance":
        gens, rcol = _F_GENERATORS, _F_RCOL_POOL
    elif style == "space":
        gens, rcol = _SP_GENERATORS, _SP_RCOL_POOL
    elif style == "military":
        gens, rcol = _MI_GENERATORS, _MI_RCOL_POOL
    elif style == "navigation":
        gens, rcol = _NAV_GENERATORS, _NAV_RCOL_POOL
    elif style == "spaceteam":
        gens, rcol = _ST_GENERATORS, _ST_RCOL_POOL
    else:
        gens, rcol = _H_GENERATORS, _H_RCOL_POOL
    return [g for g, w in gens for _ in range(w)], rcol

GEN_POOL  = []   # filled by _build_pools() at startup
RCOL_POOL = []

def random_line():
    return random.choice(GEN_POOL)()

def random_rcol_line():
    return random.choice(RCOL_POOL)()



# ══════════════════════════════════════════════════════════════════════════════
# Per-style telemetry definitions shared by sparkline/readouts widgets and
# reused as a signal source for scope-style visuals.
# Each entry: (graph_title, signal_fn, reads_list, aux_title)
#   signal_fn  : () -> float 0..1   (normalised, drives the sparkline)
#   reads_list : list of (label, value_fn, unit_str)
# ══════════════════════════════════════════════════════════════════════════════

def _gval(lo, hi):
    """Uniform random in [lo,hi], normalised to 0..1 for the sparkline."""
    v = random.uniform(lo, hi)
    return (v - lo) / (hi - lo), v

# ── hacker ────────────────────────────────────────────────────────────────────
def _gh_signal():
    return random.uniform(0, 1)
_GAUGE_HACKER = (
    "NET THROUGHPUT",
    _gh_signal,
    [
        ("CPU",    lambda: f"{random.randint(0,100):3d}",   "%"),
        ("MEM",    lambda: f"{random.randint(0,100):3d}",   "%"),
        ("NET",    lambda: f"{random.uniform(0,10):.2f}",  "Gb/s"),
        ("PKT/s",  lambda: f"{random.randint(0,999999):6d}", ""),
    ],
    "RECENT EVENTS",
)

# ── science ───────────────────────────────────────────────────────────────────
def _gs_signal():
    return random.uniform(0, 1)
_GAUGE_SCIENCE = (
    "LUMINOSITY",
    _gs_signal,
    [
        ("LUMI",   lambda: f"{random.uniform(0,1e35):.3e}", "cm⁻²s⁻¹"),
        ("ENERGY", lambda: f"{random.uniform(0,14000):.1f}", "GeV"),
        ("EVENTS", lambda: f"{random.randint(0,9999):4d}",  "/s"),
        ("TEMP",   lambda: f"{random.uniform(1,300):.1f}",  "K"),
    ],
    "DETECTOR LOG",
)

# ── medicine ──────────────────────────────────────────────────────────────────
_med_hr   = [72.0]
_med_spo2 = [98.0]
_med_bp   = [120.0]
_med_temp = [37.0]

def _gm_signal():
    # Heart-rate as normalised signal — with a beat spike every ~20 ticks
    _med_hr[0] += random.gauss(0, 0.8)
    _med_hr[0]  = max(40, min(180, _med_hr[0]))
    return (_med_hr[0] - 40) / 140   # 40bpm=0, 180bpm=1

def _gm_read_spo2():
    _med_spo2[0] = max(85.0, min(100.0, _med_spo2[0] + random.gauss(0, 0.1)))
    return f"{_med_spo2[0]:.1f}"

def _gm_read_bp():
    _med_bp[0] = max(80.0, min(200.0, _med_bp[0] + random.gauss(0, 0.5)))
    return f"{_med_bp[0]:.0f}"

def _gm_read_temp():
    _med_temp[0] = max(35.0, min(42.0, _med_temp[0] + random.gauss(0, 0.01)))
    return f"{_med_temp[0]:.1f}"

_GAUGE_MEDICINE = (
    "CARDIAC TRACE",
    _gm_signal,
    [
        ("HR",   lambda: f"{_med_hr[0]:.0f}",  "bpm"),
        ("SpO2", _gm_read_spo2,                "%"),
        ("SBP",  _gm_read_bp,                  "mmHg"),
        ("TEMP", _gm_read_temp,                "°C"),
    ],
    "MONITOR EVENTS",
)

# ── pharmacy ──────────────────────────────────────────────────────────────────
_ph_queue = [24.0]

def _gp_signal():
    _ph_queue[0] += random.gauss(0, 0.9)
    _ph_queue[0]  = max(0.0, min(80.0, _ph_queue[0]))
    return _ph_queue[0] / 80.0

_GAUGE_PHARMACY = (
    "SPIKE2 TELEMETRY",
    _gp_signal,
    [
        ("SERUM",    lambda: f"{random.uniform(0.6, 22.0):5.2f}", "mg/L"),
        ("PAW-RISE", lambda: f"{random.uniform(1.0, 28.0):5.1f}", "cmH2O"),
        ("TEMP",     lambda: f"{random.uniform(34.5, 40.0):4.1f}", "C"),
        ("CURRENT",  lambda: f"{random.uniform(0.2, 9.8):4.2f}",  "mA"),
    ],
    "SOURCE CODE",
)

# ── finance ───────────────────────────────────────────────────────────────────
_fin_price = [4500.0]

def _gf_signal():
    _fin_price[0] *= (1 + random.gauss(0, 0.003))
    _fin_price[0]  = max(100, min(99999, _fin_price[0]))
    return min(1.0, max(0.0, (_fin_price[0] - 100) / 9900))

_GAUGE_FINANCE = (
    "PRICE ACTION",
    _gf_signal,
    [
        ("PRICE", lambda: f"{_fin_price[0]:,.2f}",          ""),
        ("CHG",   lambda: f"{random.gauss(0,0.5):+.2f}",   "%"),
        ("VOL",   lambda: f"{random.randint(100,9999999):,d}", ""),
        ("VIX",   lambda: f"{random.uniform(10,80):.2f}",  ""),
    ],
    "ORDER FLOW",
)

# ── space ─────────────────────────────────────────────────────────────────────
_sp_thrust = [0.5]

def _gsp_signal():
    _sp_thrust[0] += random.gauss(0, 0.02)
    _sp_thrust[0]  = max(0.0, min(1.0, _sp_thrust[0]))
    return _sp_thrust[0]

_GAUGE_SPACE = (
    "THRUST OUTPUT",
    _gsp_signal,
    [
        ("dV",   lambda: f"{random.uniform(0,500):.2f}",   "m/s"),
        ("FUEL", lambda: f"{random.uniform(0,100):.1f}",   "%"),
        ("TEMP", lambda: f"{random.uniform(200,1500):.0f}", "K"),
        ("PWR",  lambda: f"{random.uniform(0,20000):.0f}", "W"),
    ],
    "TELEMETRY FEED",
)

# ── military ──────────────────────────────────────────────────────────────────
def _gmi_signal():
    return random.uniform(0, 1)

_GAUGE_MILITARY = (
    "THREAT INDEX",
    _gmi_signal,
    [
        ("CONTACTS", lambda: f"{random.randint(0,99):2d}",   ""),
        ("FUEL",     lambda: f"{random.randint(0,100):3d}",  "%"),
        ("AMMO",     lambda: f"{random.randint(0,999):3d}",  "rds"),
        ("COMMS",    lambda: f"{random.choice(['UP','UP','UP','DEGRADED','DOWN'])}", ""),
    ],
    "INTEL FEED",
)

# ── navigation ────────────────────────────────────────────────────────────────
_nav_speed_v = [60.0]

def _gnav_signal():
    _nav_speed_v[0] += random.gauss(0, 2)
    _nav_speed_v[0]  = max(0, min(130, _nav_speed_v[0]))
    return _nav_speed_v[0] / 130

_GAUGE_NAVIGATION = (
    "SPEED TRACE",
    _gnav_signal,
    [
        ("SPEED", lambda: f"{_nav_speed_v[0]:.0f}",         "km/h"),
        ("ETA",   lambda: f"{random.randint(1,120):3d}",    "min"),
        ("SATS",  lambda: f"{random.randint(4,18):2d}",     ""),
        ("ACC",   lambda: f"{random.uniform(1,15):.1f}",    "m"),
    ],
    "TRAFFIC ALERTS",
)

# ── spaceteam ─────────────────────────────────────────────────────────────────
def _gst_signal():
    return random.uniform(0, 1)

_GAUGE_SPACETEAM = (
    "FLUX LEVELS",
    _gst_signal,
    [
        ("FLORP",  lambda: f"{random.randint(0,11):2d}",    "WUMBLES"),
        ("BLORPS", lambda: f"{random.uniform(0,9.9):.1f}", "GLORPS"),
        ("STATUS", lambda: random.choice(["NOMINAL","BZZZT","???","OK"]), ""),
        ("T-MINUS",lambda: f"{random.randint(0,999):3d}",  "s"),
    ],
    "SYSTEM ALERTS",
)

# ── dispatch ──────────────────────────────────────────────────────────────────
_GAUGE_CONFIGS = {
    "hacker":     _GAUGE_HACKER,
    "science":    _GAUGE_SCIENCE,
    "medicine":   _GAUGE_MEDICINE,
    "pharmacy":   _GAUGE_PHARMACY,
    "finance":    _GAUGE_FINANCE,
    "space":      _GAUGE_SPACE,
    "military":   _GAUGE_MILITARY,
    "navigation": _GAUGE_NAVIGATION,
    "spaceteam":  _GAUGE_SPACETEAM,
}

def get_gauge_config(style: str):
    return _GAUGE_CONFIGS.get(style, _GAUGE_HACKER)


# ══════════════════════════════════════════════════════════════════════════════
# Per-style bar definitions for bars mode
# Each entry: (section_headers, meter_labels)
# ══════════════════════════════════════════════════════════════════════════════

_BAR_HACKER = (
    ["LOAD MAP", "ACTIVE CHANNELS", "UTILIZATION"],
    ["CPU-0", "CPU-1", "CACHE", "SOCK", "QUEUE", "TLS",
     "PKTS", "I/O", "PWR", "BUS", "TRACE", "MUX"],
)

_BAR_SCIENCE = (
    ["DETECTOR BANK", "BEAM STATUS", "INSTRUMENT LOAD"],
    ["LUMI", "ECAL", "HCAL", "TRACK", "MUON", "RF",
     "CRYO", "VAC", "DAQ", "SYNC", "TRIG", "MAG"],
)

_BAR_MEDICINE = (
    ["PATIENT MONITOR", "SYSTEM LOAD", "CLINICAL STATUS"],
    ["HR", "SpO2", "ABP", "RESP", "EtCO2", "TEMP",
     "EEG", "PUMP", "O2", "FLOW", "NIBP", "ALRM"],
)

_BAR_PHARMACY = (
    ["DISPENSARY LOAD", "ADJUDICATION", "CLINICAL FLAGS"],
    ["QUEUE", "ORDER", "FILL", "VERIFY", "READY", "PICKUP",
     "DUR", "SA", "DENIAL", "SERUM", "SPIKE2", "QC"],
)

_BAR_FINANCE = (
    ["RISK BOOK", "MARKET LOAD", "DESK UTILIZATION"],
    ["DELTA", "GAMMA", "VEGA", "VOL", "FX", "RATES",
     "EQTY", "FLOW", "VAR", "P&L", "LAT", "MM"],
)

_BAR_SPACE = (
    ["FLIGHT SYSTEMS", "SHIP STATUS", "TELEMETRY LOAD"],
    ["THRST", "FUEL", "NAV", "COMMS", "RCS", "PWR",
     "THERM", "LIFE", "RAD", "BUS", "LINK", "SCAN"],
)

_BAR_MILITARY = (
    ["TACTICAL GRID", "ASSET STATUS", "MISSION LOAD"],
    ["RADAR", "SONAR", "COMMS", "ECM", "ARM", "FUEL",
     "NAV", "DRONE", "SAT", "IFF", "CMD", "SIG"],
)

_BAR_NAVIGATION = (
    ["ROUTE STATUS", "VEHICLE LOAD", "TRAFFIC SYSTEMS"],
    ["SPEED", "ETA", "GPS", "LIDAR", "CAM", "BRAKE",
     "STEER", "LINK", "MAP", "LANE", "ACC", "PWR"],
)

_BAR_SPACETEAM = (
    ["GLORP STATUS", "FLUX SYSTEMS", "WUMBLE LOAD"],
    ["FLORP", "BLORP", "ZORP", "WUMBLE", "BEEP", "HONK",
     "QUUX", "BZZT", "GLEEP", "SPIN", "WHOOP", "DOOP"],
)

_BAR_CONFIGS = {
    "hacker": _BAR_HACKER,
    "science": _BAR_SCIENCE,
    "medicine": _BAR_MEDICINE,
    "pharmacy": _BAR_PHARMACY,
    "finance": _BAR_FINANCE,
    "space": _BAR_SPACE,
    "military": _BAR_MILITARY,
    "navigation": _BAR_NAVIGATION,
    "spaceteam": _BAR_SPACETEAM,
}

def get_bar_config(style: str):
    return _BAR_CONFIGS.get(style, _BAR_HACKER)
