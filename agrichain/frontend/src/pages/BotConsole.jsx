import { useEffect, useRef, useState } from "react";
import { Bot, MessageCircleMore, QrCode, RefreshCcw, RotateCcw, SendHorizonal, ShieldCheck, WalletCards } from "lucide-react";
import toast from "react-hot-toast";
import { agrichainApi, resolveAssetUrl } from "../services/api";

const QUICK_GROUPS = {
  Start: ["HI", "MENU", "1", "2"],
  Farmer: ["3", "4", "YES"],
  Buyer: ["5", "1", "2"],
};

const SUGGESTED_FLOWS = [
  {
    title: "Farmer listing path",
    body: "Start with HI, finish onboarding, choose sell flow, enter quantity and price, then publish the listing.",
  },
  {
    title: "Buyer order path",
    body: "Register a buyer number, browse supply, place an order, then confirm delivery once dispatch is complete.",
  },
  {
    title: "Wallet and payout path",
    body: "Top up, withdraw, and test how balance changes affect escrow and release flows.",
  },
];

export default function BotConsole() {
  const [phone, setPhone] = useState(localStorage.getItem("krishiblock-sim-phone") || "+919999000001");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [resetting, setResetting] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("krishiblock-sim-phone", phone);
  }, [phone]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [messages]);

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
      toast.success("Conversation session reset.");
    } finally {
      setResetting(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!submitting) {
        sendMessage(message);
      }
    }
  };

  return (
    <section className="page-grid bot-shell">
      <section className="hero-panel compact-panel bot-overview">
        <div className="hero-copy hero-copy-tight">
          <p className="eyebrow">WhatsApp simulation</p>
          <h1>Test onboarding, listings, orders, wallet actions, and delivery flows in a familiar chat interface.</h1>
          <p>
            This browser simulator talks to the same conversation engine used by the WhatsApp channel, but the UI is now shaped like a messaging workspace so flows are easier to understand and demo.
          </p>
          <div className="hero-stats-grid top-gap">
            <div className="summary-card">
              <span>Same backend</span>
              <strong>Conversation graph</strong>
            </div>
            <div className="summary-card">
              <span>Inline media</span>
              <strong>QR rendering</strong>
            </div>
            <div className="summary-card">
              <span>Wallet support</span>
              <strong>Top-up and release</strong>
            </div>
            <div className="summary-card">
              <span>Session scope</span>
              <strong>Per phone number</strong>
            </div>
          </div>
        </div>

        <div className="hero-rail hero-search-panel">
          <label className="field-stack" htmlFor="bot-phone">
            Test phone number
            <input
              autoComplete="tel"
              id="bot-phone"
              inputMode="tel"
              name="phone"
              onChange={(event) => setPhone(event.target.value)}
              placeholder="+919999000001"
              spellCheck={false}
              type="tel"
              value={phone}
            />
          </label>
          <div className="info-list">
            <div className="info-row">
              <WalletCards size={16} /> Use separate numbers to simulate buyer and farmer accounts.
            </div>
            <div className="info-row">
              <QrCode size={16} /> QR images generated during listing creation appear directly in the chat stream.
            </div>
            <div className="info-row">
              <ShieldCheck size={16} /> Resetting the session clears the backend conversation state for the selected phone.
            </div>
          </div>
        </div>
      </section>

      <section className="bot-layout-grid">
        <aside className="detail-card compact-panel bot-sidebar">
          <div className="section-title">
            <p className="eyebrow">Quick actions</p>
            <h3>Start a full flow in seconds</h3>
          </div>
          <div className="bot-quick-groups top-gap">
            {Object.entries(QUICK_GROUPS).map(([label, actions]) => (
              <div className="quick-group" key={label}>
                <div className="bot-quick-header">
                  <strong>{label}</strong>
                  <small>{label === "Start" ? "Kick off onboarding and navigation." : `Shortcuts for ${label.toLowerCase()} paths.`}</small>
                </div>
                <div className="quick-action-grid">
                  {actions.map((action) => (
                    <button
                      className="quick-action-pill"
                      disabled={submitting}
                      key={`${label}-${action}`}
                      onClick={() => sendMessage(action)}
                      type="button"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="section-title top-gap">
            <p className="eyebrow">Suggested runs</p>
            <h3>Best paths to demo</h3>
          </div>
          <div className="stack-list">
            {SUGGESTED_FLOWS.map((flow) => (
              <article className="list-row list-row-stacked" key={flow.title}>
                <strong>{flow.title}</strong>
                <p>{flow.body}</p>
              </article>
            ))}
          </div>
        </aside>

        <section className="chat-panel bot-device">
          <header className="bot-device-header">
            <div className="bot-contact">
              <div className="bot-avatar">
                <MessageCircleMore size={18} />
              </div>
              <div>
                <strong>KrishiBlock assistant</strong>
                <small>{phone || "Select a phone number"}</small>
              </div>
            </div>
            <div className="bot-header-actions">
              <button className="ghost-button" disabled={resetting} onClick={() => setMessages([])} type="button">
                <RefreshCcw size={15} /> Clear log
              </button>
              <button className="ghost-button" disabled={resetting} onClick={resetSession} type="button">
                <RotateCcw size={15} /> Reset session
              </button>
            </div>
          </header>

          <div aria-live="polite" className="chat-log">
            <div className="chat-day-separator">KrishiBlock flow simulator</div>
            {messages.length === 0 ? (
              <div className="chat-empty">
                <Bot size={34} />
                <strong>No messages yet.</strong>
                <p>Use a quick action like HI or MENU, or type a free-form prompt to test the conversation engine.</p>
              </div>
            ) : (
              messages.map((entry, index) => (
                <div className={`chat-message-row message-${entry.role}`} key={`${entry.role}-${index}`}>
                  <article className={`chat-bubble chat-${entry.role}`}>
                    <span className="chat-role">{entry.role === "user" ? "You" : "KrishiBlock"}</span>
                    <p>{entry.text}</p>
                    {entry.mediaUrl ? <img alt="Bot attachment" className="inline-qr" src={entry.mediaUrl} /> : null}
                    <span className="chat-meta">{entry.role === "user" ? "Sent now" : "Reply from workflow engine"}</span>
                  </article>
                </div>
              ))
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-compose-bar">
            <label className="field-stack" htmlFor="bot-message">
              Message
              <textarea
                className="chat-input"
                id="bot-message"
                name="message"
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message to test a free-text path..."
                rows={2}
                value={message}
              />
            </label>
            <button className="primary-button chat-send-button" disabled={submitting} onClick={() => sendMessage(message)} type="button">
              <SendHorizonal size={15} /> {submitting ? "Sending..." : "Send"}
            </button>
          </div>
        </section>
      </section>
    </section>
  );
}

