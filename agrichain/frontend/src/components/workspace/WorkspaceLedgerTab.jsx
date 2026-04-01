import LedgerPanel from "../ledger/LedgerPanel";

export default function WorkspaceLedgerTab({ ledger }) {
  return <LedgerPanel compact ledger={ledger} />;
}
