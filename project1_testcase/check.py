from pathlib import Path

e_path = Path("e2.bin")   # 原始
d_path = Path("2.bin")    # 解码输出
v_path = Path("v2.bin")   # 有效性标记

e = e_path.read_bytes()
d = d_path.read_bytes()
v = v_path.read_bytes()

n = min(len(e), len(d), len(v))  # auxtool: 任意一个读不到就停
valid_bits = 0
err_valid_bits = 0

for i in range(n):
    eb = e[i]
    db = d[i]
    vb = v[i]
    for _ in range(8):
        b  = eb & 1
        bd = db & 1
        bv = vb & 1
        if bv == 1:
            valid_bits += 1
            if b != bd:
                err_valid_bits += 1
        eb >>= 1; db >>= 1; vb >>= 1

if valid_bits == 0:
    print("valid_bits=0 (全部弃权或 v 文件为空)")
else:
    print(f"valid_bits={valid_bits}")
    print(f"err_valid_bits={err_valid_bits}")
    print(f"Err_valid(%)={err_valid_bits * 100.0 / valid_bits:.4f}")
