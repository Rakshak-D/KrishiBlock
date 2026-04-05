import { useDeferredValue, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import LedgerPanel from "../components/ledger/LedgerPanel";
import ErrorState from "../components/ErrorState";
import { krishiblockApi } from "../services/api";
import useAuthStore from "../store/authStore";

export default function LedgerPage() {
  const user = useAuthStore((state) => state.user);
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search.trim());
  const ledgerQuery = useQuery({
    queryKey: ["public-ledger", deferredSearch],
    queryFn: () => krishiblockApi.publicLedger(deferredSearch ? { search: deferredSearch } : {}),
  });

  if (ledgerQuery.isLoading) {
    return (
      <section className="page-grid">
        <section className="detail-card compact-panel">Loading ledger...</section>
      </section>
    );
  }

  if (ledgerQuery.isError) {
    return (
      <section className="page-grid">
        <ErrorState title="Unable to load the ledger explorer." body="Try again after the API is available." onAction={ledgerQuery.refetch} />
      </section>
    );
  }

  return (
    <section className="page-grid ledger-page">
      <section className="hero-panel hero-ledger compact-panel">
        <div className="hero-copy hero-copy-tight">
          <p className="eyebrow">Ledger explorer</p>
          <h1>Browse signed blocks, listing anchors, and escrow events without drowning in oversized cards.</h1>
          <p>
            Search by block hash, transaction ID, listing ID, order ID, crop, or signer address to trace any trade event quickly.
          </p>
          <div className="button-row">
            <Link className="primary-button" to="/market">Browse marketplace</Link>
            <Link className="ghost-button" to={user ? "/dashboard" : "/login"}>
              {user ? "Open workspace" : "Create account"}
            </Link>
          </div>
        </div>
        <div className="hero-rail hero-search-panel">
          <label className="field-stack" htmlFor="ledger-search">
            Search the chain
            <input
              id="ledger-search"
              name="search"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Block hash, listing ID, order ID, crop, or wallet"
              value={search}
            />
          </label>
          <div className="hero-stats-grid top-gap">
            <div className="summary-card">
              <span>Blocks</span>
              <strong>{ledgerQuery.data?.summary?.total_blocks || 0}</strong>
            </div>
            <div className="summary-card">
              <span>Difficulty</span>
              <strong>{ledgerQuery.data?.summary?.difficulty || 0}</strong>
            </div>
            <div className="summary-card">
              <span>Hash rate</span>
              <strong>{ledgerQuery.data?.summary?.average_hash_rate_hps || 0} H/s</strong>
            </div>
            <div className="summary-card">
              <span>Pending</span>
              <strong>{ledgerQuery.data?.summary?.mempool_pending || 0}</strong>
            </div>
          </div>
        </div>
      </section>
      <LedgerPanel ledger={ledgerQuery.data} />
    </section>
  );
}

