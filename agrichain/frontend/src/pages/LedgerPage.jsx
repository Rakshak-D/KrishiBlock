import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import LedgerPanel from "../components/ledger/LedgerPanel";
import ErrorState from "../components/ErrorState";
import { agrichainApi } from "../services/api";
import useAuthStore from "../store/authStore";

export default function LedgerPage() {
  const user = useAuthStore((state) => state.user);
  const ledgerQuery = useQuery({ queryKey: ["public-ledger"], queryFn: agrichainApi.publicLedger });

  if (ledgerQuery.isLoading) {
    return <section className="page-grid"><section className="detail-card compact-panel">Loading ledger…</section></section>;
  }

  if (ledgerQuery.isError) {
    return <section className="page-grid"><ErrorState title="Unable to load the trust ledger." body="Try again after the API is available." onAction={ledgerQuery.refetch} /></section>;
  }

  return (
    <section className="page-grid ledger-page">
      <section className="hero-panel hero-ledger compact-panel">
        <div className="hero-copy hero-copy-tight">
          <p className="eyebrow">Public trust ledger</p>
          <h1>See exactly how AgriChain uses blockchain for traceability and escrow trust.</h1>
          <p>
            Judges and users do not have to guess where blockchain helps. This page shows the listing hashes, chained wallet events,
            and public verification links that protect buyer and farmer trust.
          </p>
          <div className="button-row">
            <Link className="primary-button" to="/market">Browse marketplace</Link>
            <Link className="ghost-button" to={user ? "/dashboard" : "/login"}>{user ? "Open workspace" : "Create account"}</Link>
          </div>
        </div>
        <div className="callout-card ledger-callout">
          <span className="eyebrow">Why it matters</span>
          <strong>Escrow without proof is just another claim.</strong>
          <p>AgriChain exposes the listing anchor and the linked transaction chain so tampering is visible and verification is public.</p>
        </div>
      </section>
      <LedgerPanel ledger={ledgerQuery.data} />
    </section>
  );
}
