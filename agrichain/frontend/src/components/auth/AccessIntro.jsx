import { CheckCircle2, MessageSquareText, ShieldCheck, WalletCards } from "lucide-react";

export default function AccessIntro({ stats }) {
  return (
    <div className="auth-card auth-copy-card auth-copy-card-rich">
      <p className="eyebrow">Access AgriChain</p>
      <h1>Register on the web, continue in the bot, and manage every buyer or farmer workflow from one account.</h1>
      <p>The old “register in another app first” blocker is gone. You can now create an AgriChain account here, sign in with OTP, then move between wallet, listings, orders, verification, and bot flows without resetting context.</p>
      <div className="info-list auth-checklist">
        <div className="info-row"><CheckCircle2 size={16} /> Web registration now creates the account and starter wallet directly in `agrichain`.</div>
        <div className="info-row"><WalletCards size={16} /> Wallet, escrow, dispatch, and verification all use the same profile.</div>
        <div className="info-row"><MessageSquareText size={16} /> WhatsApp simulator still works for onboarding, but it’s no longer required for access.</div>
        <div className="info-row"><ShieldCheck size={16} /> Public traceability stays visible to buyers even without login.</div>
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
