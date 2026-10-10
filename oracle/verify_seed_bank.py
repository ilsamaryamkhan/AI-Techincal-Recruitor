"""
Verification oracle — proving the seed bank.
Runs the real checks Core AI #1 relies on:
  - hidden_test  : does the injected fault actually cause wrong output?
  - perf_test    : does the timing curve confirm the claimed complexity?
  - query_diff   : does the faulty SQL return a different result set than the correct one?
Each item is only admitted to the bank if its fault 'bites'.
"""
import time, sqlite3, textwrap

PASS, FAIL = "VERIFIED (fault bites)", "REJECTED (fault does not trigger)"
def show(title, ok): print(f"  -> {title}: {PASS if ok else FAIL}")

print("="*70); print("DOMAIN 1 — CORE SE (Python)"); print("="*70)

# ---- D1-1  EFF-LIST-IN-LOOP --------------------------------------------------
print("\n[D1-1] has_pair_with_sum — looks O(n), is O(n^2)")
def has_pair_list(nums, target):          # candidate-facing code
    seen = []
    for n in nums:
        if target - n in seen: return True
        seen.append(n)
    return False
def has_pair_set(nums, target):           # reference fix
    seen = set()
    for n in nums:
        if target - n in seen: return True
        seen.add(n)
    return False
# functional correctness (the trap: it IS correct)
cases = [([1,2,3,9],8,False),([1,2,3,9],12,True),([],5,False),([4],8,False),([4,4],8,True)]
functionally_correct = all(has_pair_list(n,t)==e for n,t,e in cases)
print(f"  functional correctness: {'correct (so a solve-check passes it)' if functionally_correct else 'broken'}")
# perf_test: confirm quadratic vs linear on worst case (no pair exists)
nums = list(range(0, 40000, 2)); target = 40001           # all even, odd target -> no pair, full scan
t0=time.perf_counter(); has_pair_list(nums,target); tl=time.perf_counter()-t0
t0=time.perf_counter(); has_pair_set(nums,target);  ts=time.perf_counter()-t0
print(f"  perf_test n=20000: list={tl*1000:.1f}ms  set={ts*1000:.1f}ms  ratio={tl/ts:.0f}x")
show("EFF-LIST-IN-LOOP", functionally_correct and tl/ts > 20)

# ---- D1-2  OOP-MUTABLE-DEFAULT ----------------------------------------------
print("\n[D1-2] add_to_cart — shared mutable default argument")
def add_to_cart(item, cart=[]):           # candidate-facing code (BUG: cart=[])
    cart.append(item); return cart
c1 = add_to_cart("apple")                 # expect ['apple']
c2 = add_to_cart("banana")                # a fresh call SHOULD be ['banana']
print(f"  call1 -> {c1}")
print(f"  call2 -> {c2}   (contaminated if it contains 'apple')")
show("OOP-MUTABLE-DEFAULT", c2 == ["apple","banana"])   # fault bites iff state bled across calls

# ---- D1-3  CORR-OFF-BY-ONE --------------------------------------------------
print("\n[D1-3] binary_search — off-by-one loop bound")
def binary_search(arr, target):           # candidate-facing code (BUG: lo < hi)
    lo, hi = 0, len(arr)-1
    while lo < hi:                         # should be lo <= hi
        mid = (lo+hi)//2
        if arr[mid]==target: return mid
        elif arr[mid]<target: lo = mid+1
        else: hi = mid-1
    return -1
arr=[1,3,5,7,9]
got, expected = binary_search(arr,9), 4    # 9 is the last element
print(f"  search([1,3,5,7,9], 9) -> {got}  (expected {expected})")
show("CORR-OFF-BY-ONE", got != expected)   # fault bites iff it misses the boundary element

print("\n"+"="*70); print("DOMAIN 3 — DATABASE (SQL)"); print("="*70)
db = sqlite3.connect(":memory:"); cur = db.cursor()
cur.executescript("""
CREATE TABLE customers(id INT, name TEXT, city TEXT);
CREATE TABLE orders(id INT, customer_id INT, total REAL);
CREATE TABLE order_tags(order_id INT, tag TEXT);
INSERT INTO customers VALUES (1,'Ayesha','Lahore'),(2,'Bilal','Karachi'),(3,'Chaudhry','Lahore');
INSERT INTO orders VALUES (10,1,5000),(11,1,3000),(12,2,2000);  -- customer 3 has NO orders
INSERT INTO order_tags VALUES (10,'urgent'),(10,'gift'),(10,'fragile'),(11,'urgent');
""")
def one(q): cur.execute(q); return cur.fetchone()[0]
def rows(q): cur.execute(q); return cur.fetchall()

# ---- D3-1  DB-WRONG-JOIN (row inflation) ------------------------------------
print("\n[D3-1] total revenue — join to one-to-many inflates SUM")
faulty = one("SELECT SUM(o.total) FROM orders o JOIN order_tags t ON o.id=t.order_id")
correct= one("SELECT SUM(total) FROM orders")
print(f"  faulty (joined to tags): {faulty}")
print(f"  correct (orders only)  : {correct}")
show("DB-WRONG-JOIN", faulty != correct)

# ---- D3-2  DB-GROUPBY-ERR (COUNT(*) over LEFT JOIN counts NULL row) ----------
print("\n[D3-2] orders per customer — COUNT(*) miscounts zero-order customer")
faulty = rows("""SELECT c.name, COUNT(*)      FROM customers c
                 LEFT JOIN orders o ON c.id=o.customer_id GROUP BY c.name ORDER BY c.name""")
correct= rows("""SELECT c.name, COUNT(o.id)   FROM customers c
                 LEFT JOIN orders o ON c.id=o.customer_id GROUP BY c.name ORDER BY c.name""")
print(f"  faulty  COUNT(*)   : {faulty}")
print(f"  correct COUNT(o.id): {correct}")
# fault bites iff the zero-order customer (Chaudhry) is reported as 1 instead of 0
bites = dict(faulty)["Chaudhry"]==1 and dict(correct)["Chaudhry"]==0
show("DB-GROUPBY-ERR", bites)

print("\n"+"="*70); print("All items that printed VERIFIED are admitted to the bank."); print("="*70)
