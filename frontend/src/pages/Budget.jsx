import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useApp } from '../App'
import { ErrorBox, Loading, Modal, MoneyInput, MonthPicker, Section, Table, Field, useApi, useToast } from '../components/ui'
import { rp, rpShort, thisMonth, pct } from '../fmt'

export default function Budget() {
  const { can, settings } = useApp()
  const toast = useToast()
  const [month, setMonth] = useState(thisMonth())
  const { data: d, error, reload } = useApi(`/api/budget?month=${month}`)
  const [edit, setEdit] = useState(null)
  const [val, setVal] = useState(0)
  const [notes, setNotes] = useState('')
  const [err, setErr] = useState('')
  const save = async () => {
    try { await api('/api/budget', { method: 'PUT', body: { month, category: edit.category, plannedRp: val, notes } }); toast('Plan budget disimpan'); setEdit(null); reload() } catch (e) { setErr(e.message) }
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><h1 className="text-xl font-extrabold">Budget KOL</h1><p className="text-sm text-ink/60">Plan per kategori → dialokasikan ke campaign → committed saat booking DEAL</p></div>
        <MonthPicker value={month} onChange={setMonth} />
      </div>
      <ErrorBox msg={error} />
      {!d ? <Loading /> : (
        <Section title={`Pagu bulanan ${rpShort(d.pagu)} · plan ${rpShort(d.total.plannedRp)}`}>
          <Table head={['Kategori', { label: 'Plan', right: 1 }, { label: 'Dialokasikan ke campaign', right: 1 }, { label: 'Committed (DEAL+)', right: 1 }, { label: 'Dibayar', right: 1 }, { label: 'Sisa', right: 1 }, 'Pemakaian', 'Campaign', '']}>
            {d.rows.map((r) => (
              <tr key={r.category} className={r.warn ? 'bg-amber-50' : ''}>
                <td className="td font-semibold">{r.category}</td>
                <td className="td text-right num font-semibold">{rp(r.plannedRp)}</td>
                <td className="td text-right num">{rp(r.allocatedRp)}</td>
                <td className="td text-right num">{rp(r.committedRp)}</td>
                <td className="td text-right num">{rp(r.paidRp)}</td>
                <td className={`td text-right num ${r.remainingRp < 0 ? 'text-brand font-bold' : ''}`}>{rp(r.remainingRp)}</td>
                <td className="td w-36">
                  <div className="h-2 overflow-hidden rounded-full bg-brand-soft"><div className={`bar-grow h-full rounded-full ${r.warn ? 'bg-warn' : 'bg-brand'}`} style={{ width: `${Math.min(100, r.plannedRp ? (r.committedRp / r.plannedRp) * 100 : 0)}%` }} /></div>
                  <div className="text-[11px] text-ink/60">{r.plannedRp ? pct(r.committedRp / r.plannedRp, 0) : '–'}{r.warn && ' · > 90%'}</div>
                </td>
                <td className="td text-xs">{r.campaigns.map((c) => <div key={c.id}><Link className="text-brand underline" to={`/campaign/${c.id}`}>{c.name}</Link> {rpShort(c.budgetRp)}{c.code && ` · ${c.code}`}</div>)}</td>
                <td className="td">{can('Manager') && <button className="btn-ghost btn-sm" onClick={() => { setEdit(r); setVal(r.plannedRp); setNotes(r.notes || ''); setErr('') }}>Ubah</button>}</td>
              </tr>
            ))}
            <tr className="font-bold"><td className="td">Total</td><td className="td text-right num">{rp(d.total.plannedRp)}</td><td className="td text-right num">{rp(d.total.allocatedRp)}</td><td className="td text-right num">{rp(d.total.committedRp)}</td><td className="td text-right num">{rp(d.total.paidRp)}</td><td className="td text-right num">{rp(d.total.remainingRp)}</td><td className="td" colSpan={3}></td></tr>
          </Table>
          <p className="mt-2 text-xs text-ink/50">Pagu bulanan diatur di Pengaturan (sekarang {rp(settings.monthlyKolPagu)}). Campaign tidak bisa dibuat melebihi sisa plan kategorinya; booking tidak bisa DEAL melebihi sisa budget campaign.</p>
        </Section>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={`Plan ${edit?.category} · ${month}`} footer={<><button className="btn-ghost" onClick={() => setEdit(null)}>Batal</button><button className="btn-primary" onClick={save}>Simpan</button></>}>
        <div className="space-y-3">
          <Field label="Plan budget (Rp)"><MoneyInput value={val} onChange={setVal} /></Field>
          <Field label="Catatan"><input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="mis. selaras inisiatif N01" /></Field>
          <ErrorBox msg={err} />
        </div>
      </Modal>
    </div>
  )
}
