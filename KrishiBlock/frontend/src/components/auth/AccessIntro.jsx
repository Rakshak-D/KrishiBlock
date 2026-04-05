import { CheckCircle2, MessageSquareText, ShieldCheck, WalletCards } from "lucide-react";

export default function AccessIntro({ stats }) {
  return (
    <div className="auth-card auth-copy-card auth-copy-card-rich">
      <p className="eyebrow">KrishiBlock access</p>
      <h1>One identity for marketplace, escrow, wallet, verification, and WhatsApp flows.</h1>
      <p>
        Register once, sign in with OTP when you return, and keep the same account across the web workspace and conversation channel.
      </p>
      <div className="info-list auth-checklist">
        <div className="info-row"><CheckCircle2 size={16} /> Account setup creates the profile, wallet, and blockchain identity together.</div>
        <div className="info-row"><WalletCards size={16} /> Wallet, escrow, dispatch, and payout history stay tied to the same account.</div>
        <div className="info-row"><MessageSquareText size={16} /> The browser simulator mirrors the same conversation engine used for WhatsApp.</div>
        <div className="info-row"><ShieldCheck size={16} /> Public verification remains available even before sign-in.</div>
      </div>
      <div className="hero-stats-grid top-gap">
        <div className="summary-card"><span>Listings live</span><strong>{stats.totalListings}</strong></div>
        <div className="summary-card"><span>Active farmers</span><strong>{stats.activeFarmers}</strong></div>
        <div className="summary-card"><span>Local avg</span><strong>{stats.localAverage}</strong></div>
        <div className="summary-card"><span>Global avg</span><strong>{stats.globalAverage}</strong></div>
      </div>
    </div>
  );
}
