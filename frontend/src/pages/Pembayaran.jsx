import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fileUrl } from '../api'
import { useApp } from '../App'
import { ErrorBox, Field, FileDrop, Loading, Modal, MoneyInput, Section, StatusBadge, Table, TierBadge, useApi, useToast } from '../components/ui'
import { date, rp } from '../fmt'

export default function Pembayaran() {
  const { can, user } = useApp()
  const { data: d, error, reload } = useApi('/api/payments')
  const [pay, setPay] = useState(null)
  const [tab, setTab] = useState('queue')
  if (error) return <ErrorBox msg={error} />
  if (!d) return <Loading />
  const fin = can('Finance', 'Manager')
  const rows = d[tab]
  return (
    <div className="space-y-4">
      <div><h1 className="text-xl font-extrabold">Pembayaran KOL</h1><p className="text-sm text-ink/60">Pelunasan hanya untuk booking yang report H+7-nya sudah di-approve KOL TL.</p></div>
      <div className="flex gap-2">
        {[['queue', `Siap dilunasi (${d.queue.length})`], ['running', `Berjalan / DP (${d.running.length})`], ['paid', `Lunas (${d.paid.length})`]].map(([k, l]) => <button key={k} onClick={() => setTab(k)} className={`btn-sm btn ${tab === k ? 'bg-brand text-white' : 'border border-brand-line'}`}>{l}</button>)}
      </div>
      <div className="space-y-2 sm:hidden">
        {!rows.length && <p className="card p-4 text-sm text-ink/50">Kosong.</p>}
        {rows.map((b) => {
          const dp = b.payment?.dpRp || 0
          return (
            <div key={b.id} className="card p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0"><Link to={`/booking/${b.id}`} className="font-bold">{b.kol.name}</Link> <TierBadge t={b.tierAtBooking} /><div className="truncate text-xs text-ink/60">{b.campaign.category} · {b.campaign.name}</div></div>
                <StatusBadge s={b.status} />
              </div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                <div><div className="text-ink/50">Kontrak</div><div className="num font-semibold">{rp(b.totalCostRp)}</div></div>
                <div><div className="text-ink/50">DP</div><div className="num">{rp(dp)}</div></div>
                <div><div className="text-ink/50">{tab === 'paid' ? 'Lunas' : 'Sisa'}</div><div className="num font-bold">{tab === 'paid' ? date(b.payment?.paidAt) : rp(b.totalCostRp + (b.commissionDue || 0) - dp)}</div></div>
              </div>
              {b.commissionDue > 0 && tab !== 'paid' && <div className="mt-1 text-[11px] text-ink/50">Sisa termasuk komisi {rp(b.commissionDue)}</div>}
              <div className="mt-1 text-xs text-ink/60">Rekening: {b.kolBank || '—'}</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {fin && tab === 'queue' && <button className="btn-ok btn-sm flex-1" onClick={() => setPay({ b, mode: 'pay' })}>Lunasi</button>}
                {fin && tab === 'running' && !dp && <button className="btn-ghost btn-sm flex-1" onClick={() => setPay({ b, mode: 'dp' })}>Catat DP</button>}
                {user.role === 'Manager' && tab === 'running' && <button className="btn-ghost btn-sm" onClick={() => setPay({ b, mode: 'override' })}>Override</button>}
                {tab === 'paid' && b.payment?.proof?.map((p) => <a key={p} href={fileUrl(p)} target="_blank" rel="noreferrer" className="text-xs text-brand underline">bukti transfer</a>)}
              </div>
            </div>
          )
        })}
      </div>
      <Section className="hidden sm:block">
        {!rows.length ? <p className="text-sm text-ink/50">Kosong.</p> : (
          <Table head={['KOL', 'Campaign', 'Status', { label: 'Total kontrak', right: 1 }, { label: 'DP', right: 1 }, { label: 'Sisa', right: 1 }, 'Rekening', '']}>
            {rows.map((b) => {
              const dp = b.payment?.dpRp || 0
              return (
                <tr key={b.id}>
                  <td className="td"><Link to={`/booking/${b.id}`} className="font-semibold hover:text-brand">{b.kol.name}</Link> <TierBadge t={b.tierAtBooking} /></td>
                  <td className="td text-xs">{b.campaign.name}<div className="text-ink/50">{b.campaign.category}</div></td>
                  <td className="td"><StatusBadge s={b.status} />{b.reportApprovedBy && <div className="text-[11px] text-ink/50">approved {b.reportApprovedBy}</div>}</td>
                  <td className="td text-right num">{rp(b.totalCostRp)}</td>
                  <td className="td text-right num">{rp(dp)}</td>
                  <td className="td text-right num font-semibold">{tab === 'paid' ? rp(0) : rp(b.totalCostRp + (b.commissionDue || 0) - dp)}{b.commissionDue > 0 && tab !== 'paid' && <div className="text-[11px] font-normal text-ink/50">incl. komisi {rp(b.commissionDue)}</div>}</td>
                  <td className="td text-xs">{b.kolBank || '—'}</td>
                  <td className="td whitespace-nowrap">
                    {fin && tab === 'queue' && <button className="btn-ok btn-sm" onClick={() => setPay({ b, mode: 'pay' })}>Lunasi</button>}
                    {fin && tab === 'running' && !dp && <button className="btn-ghost btn-sm" onClick={() => setPay({ b, mode: 'dp' })}>Catat DP</button>}
                    {user.role === 'Manager' && tab === 'running' && <button className="btn-ghost btn-sm ml-1" onClick={() => setPay({ b, mode: 'override' })}>Override</button>}
                    {tab === 'paid' && b.payment?.proof?.map((p) => <a key={p} href={fileUrl(p)} target="_blank" rel="noreferrer" className="text-xs text-brand underline">bukti</a>)}
                    {tab === 'paid' && <div className="text-[11px] text-ink/50">{date(b.payment?.paidAt)}</div>}
                  </td>
                </tr>
              )
            })}
          </Table>
        )}
      </Section>
      <PayModal x={pay} onClose={() => setPay(null)} onDone={reload} />
    </div>
  )
}

function PayModal({ x, onClose, onDone }) {
  const toast = useToast()
  const [amt, setAmt] = useState(0)
  const [proof, setProof] = useState([])
  const [inv, setInv] = useState([])
  const [reason, setReason] = useState('')
  const [err, setErr] = useState('')
  const [lastId, setLastId] = useState(null)
  if (x && x.b.id + x.mode !== lastId) {
    setLastId(x.b.id + x.mode); setErr(''); setProof([]); setInv([]); setReason('')
    const dp = x.b.payment?.dpRp || 0
    setAmt(x.mode === 'dp' ? Math.round(x.b.totalCostRp / 2) : x.b.totalCostRp + (x.b.commissionDue || 0) - dp)
  }
  if (!x) return null
  const submit = async () => {
    try {
      await api(`/api/bookings/${x.b.id}/${x.mode === 'dp' ? 'dp' : 'pay'}`, { method: 'POST', body: { amountRp: amt, proofFiles: proof, invoiceFiles: inv, overrideReason: x.mode === 'override' ? reason : '' } })
      toast(x.mode === 'dp' ? 'DP tercatat' : 'Booking lunas'); setLastId(null); onClose(); onDone()
    } catch (e) { setErr(e.message) }
  }
  return (
    <Modal open onClose={() => { setLastId(null); onClose() }} title={`${x.mode === 'dp' ? 'Catat DP' : x.mode === 'override' ? 'Override pelunasan (Manager)' : 'Pelunasan'} · ${x.b.kol.name}`}
      footer={<><button className="btn-ghost" onClick={() => { setLastId(null); onClose() }}>Batal</button><button className="btn-ok" onClick={submit}>Simpan</button></>}>
      <div className="space-y-3">
        {x.mode === 'override' && <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-brand">Report belum di-approve. Override tercatat di audit log dan muncul di laporan.</p>}
        <Field label="Nominal (Rp)"><MoneyInput value={amt} onChange={setAmt} /></Field>
        <Field label="Bukti transfer *"><FileDrop files={proof} onChange={setProof} label="Bukti" accept="image/*,application/pdf" /></Field>
        {x.mode !== 'dp' && <Field label="Invoice KOL"><FileDrop files={inv} onChange={setInv} label="Invoice" accept="image/*,application/pdf" /></Field>}
        {x.mode === 'override' && <Field label="Alasan tertulis (min. 10 karakter)"><textarea className="input min-h-[72px] py-2" value={reason} onChange={(e) => setReason(e.target.value)} /></Field>}
        <ErrorBox msg={err} />
      </div>
    </Modal>
  )
}
