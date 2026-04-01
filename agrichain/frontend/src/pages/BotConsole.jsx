import { useEffect, useState } from "react";
import { Bot, QrCode, RefreshCcw, RotateCcw, SendHorizonal, WalletCards } from "lucide-react";
import toast from "react-hot-toast";
import { agrichainApi, resolveAssetUrl } from "../services/api";

const QUICK_GROUPS = {
  Start: ["HI", "MENU", "1", "2"],
  Farmer: ["3", "4", "YES"],
  Buyer: ["5", "1", "2"],
};

export default function BotConsole() {
  const [phone, setPhone] = useState(localStorage.getItem("agrichain-sim-phone") || "+919999000001");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    localStorage.setItem("agrichain-sim-phone", phone);
  }, [phone]);

  const sendMessage = async (draft) => {
    const text = String(draft || message).trim();
    if (!text) {
      toast.error("Enter a message or use a quick action.");
      return;
    }
    setSubmitting(true);
    try {
      setMessages((current) => [...current, { role: "user", text }]);
      const payload = await agrichainApi.simulateMessage({ phone: phone.trim(), message: text });
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: payload.response,
          mediaUrl: resolveAssetUrl(payload.media_url),
        },
      ]);
      setMessage("");
    } finally {
      setSubmitting(false);
    }
  };

  const resetSession = async () => {
    setResetting(true);
    try {
      await agrichainApi.resetSimulatedSession({ phone: phone.trim() });
      setMessages([]);
      toast.success("Simulator session reset.");
    } finally {
      setResetting(false);
    }
  };

  return (
    <section className="page-grid bot-shell">
      <section className="hero-panel hero-marketplace compact-panel">
        <div className="hero-copy hero-copy-tight">
          <p className="eyebrow">Bot operations lab</p>
          <h1>Test registration, wallet, buy, sell, and delivery flows without needing live WhatsApp delivery.</h1>
          <p>The simulator still runs the same conversation engine. It’s now styled and positioned like part of the same product instead of a separate prototype screen.</p>
          <div className="hero-stats-grid top-gap">
            <div className="summary-card"><span>Same engine</span><strong>Conversation graph</strong></div>
            <div className="summary-card"><span>Wallet actions</span><strong>Top-up and release</strong></div>
            <div className="summary-card"><span>QR output</span><strong>Inline rendering</strong></div>
            <div className="summary-card"><span>Session scope</span><strong>Per phone</strong></div>
          </div>
        </div>
        <div className="hero-rail hero-search-panel">
          <label className="field-stack" htmlFor="bot-phone">
            Test phone number
            <input autoComplete="tel" id="bot-phone" inputMode="tel" name="phone" onChange={(event) => setPhone(event.target.value)} placeholder="+919999000001…" spellCheck={false} type="tel" value={phone} />
          </label>
          <div className="bot-quick-groups">
            {Object.entries(QUICK_GROUPS).map(([label, actions]) => (
              <div className="quick-group" key={label}>
                <span>{label}</span>
                <div className="badge-row">
                  {actions.map((action) => (
                    <button className="ghost-button" disabled={submitting} key={`${label}-${action}`} onClick={() => sendMessage(action)} type="button">
                      {action}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="info-list">
            <div className="info-row"><WalletCards size={16} /> Use separate phone numbers to simulate buyer and farmer accounts.</div>
            <div className="info-row"><QrCode size={16} /> QR images generated during listing creation appear inline here.</div>
          </div>
        </div>
      </section>

      <div className="dashboard-grid bot-layout">
        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Suggested journeys</p>
            <h3>Run full flows quickly</h3>
          </div>
          <div className="stack-list top-gap">
            <div className="list-row list-row-stacked"><strong>Farmer onboarding to listing</strong><p>HI, registration, market choice, sell flow, quantity, price, publish.</p></div>
            <div className="list-row list-row-stacked"><strong>Buyer order path</strong><p>Register a buyer phone, browse, place an order, then track the release-key confirmation flow.</p></div>
            <div className="list-row list-row-stacked"><strong>Wallet support flow</strong><p>Top up, withdraw, then resume a blocked order after the balance changes.</p></div>
          </div>
        </section>

        <section className="chat-panel">
          <div className="section-header compact-header">
            <div>
              <p className="eyebrow">Live conversation</p>
              <h2>{messages.length ? "Simulator running" : "Start with HI or MENU"}</h2>
            </div>
            <div className="button-row">
              <button className="ghost-button" disabled={resetting} onClick={() => setMessages([])} type="button"><RefreshCcw size={15} /> Clear local log</button>
              <button className="ghost-button" disabled={resetting} onClick={resetSession} type="button"><RotateCcw size={15} /> Reset session</button>
            </div>
          </div>

          <div className="chat-log top-gap" aria-live="polite">
            {messages.length === 0 ? (
              <div className="chat-empty">
                <Bot size={34} />
                <strong>No messages yet.</strong>
                <p>Use the quick-reply groups or type a free-form message to exercise the workflow engine.</p>
              </div>
            ) : (
              messages.map((entry, index) => (
                <article className={`chat-bubble chat-${entry.role}`} key={`${entry.role}-${index}`}>
                  <span className="chat-role">{entry.role === "user" ? "You" : "AgriChain"}</span>
                  <p>{entry.text}</p>
                  {entry.mediaUrl ? <img alt="Bot attachment" className="inline-qr" height="220" src={entry.mediaUrl} width="220" /> : null}
                </article>
              ))
            )}
          </div>

          <div className="chat-compose top-gap">
            <label className="field-stack" htmlFor="bot-message">
              Message
              <textarea
                id="bot-message"
                name="message"
                rows={3}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Type a message to test a free-text path…"
              />
            </label>
            <button className="primary-button" disabled={submitting} onClick={() => sendMessage(message)} type="button">
              <SendHorizonal size={15} /> {submitting ? "Sending…" : "Send"}
            </button>
          </div>
        </section>
      </div>
    </section>
  );
}
