import { useState } from "react";

const API = "http://localhost:8000";

function App() {
  const [screen, setScreen] = useState("login");
  const [token, setToken] = useState("");
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [orders, setOrders] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [form, setForm] = useState({ username: "", password: "", item: "", quantity: 1 });

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const register = async () => {
    setError(""); setSuccess("");
    const res = await fetch(`${API}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: form.username, password: form.password, role: "user" })
    });
    const data = await res.json();
    if (res.ok) setSuccess("Registered! Now login.");
    else setError(data.detail || "Registration failed");
  };

  const login = async () => {
    setError(""); setSuccess("");
    const res = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: form.username, password: form.password })
    });
    const data = await res.json();
    if (res.ok) {
      setToken(data.access_token);
      setUsername(form.username);
      setScreen("orders");
    } else setError(data.detail || "Login failed");
  };

  const placeOrder = async () => {
    setError(""); setSuccess("");
    const res = await fetch(`${API}/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({
        item: form.item,
        quantity: parseInt(form.quantity),
        idempotency_key: `${username}-${form.item}-${Date.now()}`
      })
    });
    const data = await res.json();
    if (res.ok) {
      setSuccess(`Order placed! ID: ${data.order_id}`);
      fetchOrders();
      setTimeout(fetchNotifications, 3000);
    } else setError(data.detail || "Order failed");
  };

  const fetchOrders = async () => {
    const res = await fetch(`${API}/orders`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();
    if (res.ok) setOrders(data);
  };

  const fetchNotifications = async () => {
    const res = await fetch(`${API}/notifications/${username}`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();
    if (res.ok) setNotifications(data);
  };

  const styles = {
    app: { fontFamily: "sans-serif", maxWidth: 600, margin: "40px auto", padding: 24 },
    card: { background: "#f9f9f9", borderRadius: 12, padding: 24, marginBottom: 20, boxShadow: "0 2px 8px rgba(0,0,0,0.08)" },
    input: { width: "100%", padding: "10px 12px", marginBottom: 12, borderRadius: 8, border: "1px solid #ddd", fontSize: 14, boxSizing: "border-box" },
    btn: { padding: "10px 20px", borderRadius: 8, border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, marginRight: 8 },
    primary: { background: "#2563eb", color: "#fff" },
    secondary: { background: "#e5e7eb", color: "#111" },
    danger: { background: "#dc2626", color: "#fff" },
    error: { color: "#dc2626", marginBottom: 12, fontSize: 14 },
    success: { color: "#16a34a", marginBottom: 12, fontSize: 14 },
    nav: { display: "flex", gap: 8, marginBottom: 24 },
    tag: { padding: "4px 10px", borderRadius: 20, fontSize: 12, fontWeight: 600, background: "#dbeafe", color: "#1d4ed8" },
    notif: { background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: 12, marginBottom: 8, fontSize: 14 },
    order: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8, padding: 12, marginBottom: 8, fontSize: 14 },
  };

  return (
    <div style={styles.app}>
      <h2 style={{ marginBottom: 4 }}>Microservices App</h2>
      <p style={{ color: "#6b7280", marginBottom: 24, fontSize: 14 }}>
        {token ? `Logged in as ${username}` : "Not logged in"}
      </p>

      {token && (
        <div style={styles.nav}>
          <button style={{ ...styles.btn, ...(screen === "orders" ? styles.primary : styles.secondary) }} onClick={() => { setScreen("orders"); fetchOrders(); }}>Orders</button>
          <button style={{ ...styles.btn, ...(screen === "notifications" ? styles.primary : styles.secondary) }} onClick={() => { setScreen("notifications"); fetchNotifications(); }}>Notifications</button>
          <button style={{ ...styles.btn, ...styles.danger }} onClick={() => { setToken(""); setUsername(""); setScreen("login"); }}>Logout</button>
        </div>
      )}

      {error && <div style={styles.error}>⚠ {error}</div>}
      {success && <div style={styles.success}>✓ {success}</div>}

      {/* LOGIN / REGISTER */}
      {screen === "login" && (
        <div style={styles.card}>
          <h3 style={{ marginTop: 0 }}>Login / Register</h3>
          <input style={styles.input} name="username" placeholder="Username" onChange={handle} />
          <input style={styles.input} name="password" type="password" placeholder="Password" onChange={handle} />
          <button style={{ ...styles.btn, ...styles.primary }} onClick={login}>Login</button>
          <button style={{ ...styles.btn, ...styles.secondary }} onClick={register}>Register</button>
        </div>
      )}

      {/* ORDERS */}
      {screen === "orders" && (
        <>
          <div style={styles.card}>
            <h3 style={{ marginTop: 0 }}>Place Order</h3>
            <input style={styles.input} name="item" placeholder="Item (e.g. laptop)" onChange={handle} />
            <input style={styles.input} name="quantity" type="number" placeholder="Quantity" defaultValue={1} onChange={handle} />
            <button style={{ ...styles.btn, ...styles.primary }} onClick={placeOrder}>Place Order</button>
          </div>
          <div style={styles.card}>
            <h3 style={{ marginTop: 0 }}>Your Orders</h3>
            {orders.length === 0 && <p style={{ color: "#6b7280", fontSize: 14 }}>No orders yet.</p>}
            {orders.map(o => (
              <div key={o.order_id} style={styles.order}>
                <span style={styles.tag}>{o.status}</span>
                <strong style={{ marginLeft: 8 }}>{o.item}</strong>
                <span style={{ color: "#6b7280", marginLeft: 8 }}>x{o.quantity}</span>
                <div style={{ color: "#9ca3af", fontSize: 12, marginTop: 4 }}>{o.order_id}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* NOTIFICATIONS */}
      {screen === "notifications" && (
        <div style={styles.card}>
          <h3 style={{ marginTop: 0 }}>Notifications</h3>
          {notifications.length === 0 && <p style={{ color: "#6b7280", fontSize: 14 }}>No notifications yet.</p>}
          {notifications.map((n, i) => (
            <div key={i} style={styles.notif}>
              <strong>{n.event_type}</strong>
              <p style={{ margin: "4px 0 0" }}>{n.message}</p>
              <div style={{ color: "#9ca3af", fontSize: 12 }}>{n.order_id}</div>
            </div>
          ))}
          <button style={{ ...styles.btn, ...styles.secondary, marginTop: 8 }} onClick={fetchNotifications}>Refresh</button>
        </div>
      )}
    </div>
  );
}

export default App;