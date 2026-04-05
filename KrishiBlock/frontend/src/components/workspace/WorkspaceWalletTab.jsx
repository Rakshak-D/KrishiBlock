import TransactionTable from "../TransactionTable";

export default function WorkspaceWalletTab({ overview, walletMode, amount, upiId, amountError, upiError, submitting, setAmount, setUpiId, setWalletMode, onSubmitWalletAction, transactions }) {
  return (
    <div className="dashboard-grid dashboard-grid-wide">
      <section className="detail-card compact-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Wallet balance</p>
            <h2>{overview.wallet.balance_display}</h2>
          </div>
          <span className="chip chip-soft">Locked {overview.wallet.locked_balance_display}</span>
        </div>

        <div className="hero-stats-grid top-gap">
          <div className="summary-card">
            <span>Available</span>
            <strong>{overview.wallet.balance_display}</strong>
          </div>
          <div className="summary-card">
            <span>Locked</span>
            <strong>{overview.wallet.locked_balance_display}</strong>
          </div>
          <div className="summary-card">
            <span>Entries</span>
            <strong>{transactions.length}</strong>
          </div>
          <div className="summary-card">
            <span>Status</span>
            <strong>{walletMode ? "Action open" : "Ready"}</strong>
          </div>
        </div>

        <div className="button-row top-gap">
          <button className="primary-button" onClick={() => setWalletMode("add")} type="button">Add funds</button>
          <button className="ghost-button" onClick={() => setWalletMode("withdraw")} type="button">Withdraw to UPI</button>
        </div>

        {walletMode ? (
          <div className="stack-list top-gap">
            <label className="field-stack" htmlFor="wallet-amount">
              Amount
              <input id="wallet-amount" inputMode="decimal" min="0.1" name="amount" onChange={(event) => setAmount(event.target.value)} placeholder="1000" step="0.01" type="number" value={amount} />
              {amountError ? <small className="field-error">{amountError}</small> : null}
            </label>
            {walletMode === "withdraw" ? (
              <label className="field-stack" htmlFor="wallet-upi">
                UPI ID
                <input autoComplete="off" id="wallet-upi" inputMode="email" name="upi_id" onChange={(event) => setUpiId(event.target.value)} placeholder="name@bank" spellCheck={false} type="text" value={upiId} />
                {upiError ? <small className="field-error">{upiError}</small> : null}
              </label>
            ) : null}
            <div className="button-row">
              <button className="primary-button" disabled={submitting || Boolean(amountError || upiError)} onClick={onSubmitWalletAction} type="button">{submitting ? "Submitting..." : "Submit"}</button>
              <button className="ghost-button" onClick={() => setWalletMode("")} type="button">Close</button>
            </div>
          </div>
        ) : null}
      </section>

      <section className="detail-card compact-panel">
        <TransactionTable transactions={transactions} />
      </section>
    </div>
  );
}
