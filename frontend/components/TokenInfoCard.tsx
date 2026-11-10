import type { TokenInfo } from "@/types";
import { Card } from "@/components/Card";
import { formatBig, shortAddress } from "@/lib/format";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/60 py-2 last:border-0">
      <span className="text-sm text-muted">{label}</span>
      <span className="text-right text-sm text-slate-200">{value}</span>
    </div>
  );
}

export function TokenInfoCard({ token }: { token: TokenInfo }) {
  return (
    <Card>
      <h3 className="mb-3 text-lg font-semibold">
        {token.metadata.name ?? "Unknown token"}{" "}
        <span className="text-muted">{token.metadata.symbol ? `(${token.metadata.symbol})` : ""}</span>
      </h3>
      <div className="grid gap-x-8 md:grid-cols-2">
        <Row label="Address" value={<code className="text-xs">{shortAddress(token.address, 8)}</code>} />
        <Row label="Chain" value={`${token.chain_name} (${token.chain_id})`} />
        <Row label="Decimals" value={token.metadata.decimals ?? "—"} />
        <Row label="Total supply" value={formatBig(token.metadata.total_supply)} />
        <Row label="Owner" value={<code className="text-xs">{token.owner ? shortAddress(token.owner) : "none detected"}</code>} />
        <Row label="Contract type" value={token.contract_type} />
        <Row label="ERC-20 compliant" value={token.erc20_compliant ? "yes" : "no / unverified"} />
        <Row label="Verified source" value={token.is_verified === null ? "unknown" : token.is_verified ? "yes" : "no"} />
        <Row
          label="Proxy"
          value={token.proxy.is_proxy ? `yes (${token.proxy.proxy_type})` : "no"}
        />
        <Row label="Bytecode size" value={`${token.bytecode_size} bytes`} />
      </div>
      {token.proxy.is_proxy && token.proxy.implementation && (
        <p className="mt-3 text-xs text-muted">
          Implementation: <code>{shortAddress(token.proxy.implementation, 8)}</code>
        </p>
      )}
      {token.pairs.length > 0 && (
        <p className="mt-3 text-xs text-muted">
          Liquidity pairs: {token.pairs.map((p) => p.dex_name).join(", ")}
        </p>
      )}
    </Card>
  );
}
