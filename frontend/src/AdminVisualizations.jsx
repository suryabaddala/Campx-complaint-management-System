import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { BarChart3 } from "lucide-react";

const COLORS = ["#4567f5", "#20b997", "#ffad61", "#845ef7", "#ec6b84", "#43a5c8"];

function EmptyChart({ title, children }) {
  return <div className="chart-empty"><span><BarChart3 size={17} /></span><strong>{title}</strong><p>{children}</p></div>;
}

function AnalyticsBreakdown({ title, eyebrow, items, color }) {
  const maxValue = Math.max(1, ...items.map((item) => item.value));
  return <section className="panel mini-chart-panel"><div className="section-kicker">{eyebrow}</div><h2>{title}</h2>{items.length ? <div className="mini-bars">{items.map((item) => <div className="mini-bar-row" key={item.name}><span title={item.name}>{item.name}</span><div className="mini-bar-track"><i style={{ width: `${Math.max(4, (item.value / maxValue) * 100)}%`, background: color }} /></div><strong>{item.value}</strong></div>)}</div> : <p className="quiet-copy">No data yet.</p>}</section>;
}

export default function AdminVisualizations({ analytics, busy }) {
  return <>
    <div className="analytics-grid"><section className="panel chart-panel"><div className="chart-heading"><div><div className="section-kicker">A LITTLE CONTEXT</div><h2>Reports over time</h2></div><span className="chart-caption">Recent activity</span></div>{busy ? <div className="chart-skeleton" /> : analytics?.trend?.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={analytics.trend} margin={{ left: -20, right: 8, top: 16, bottom: 0 }}><defs><linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#526df5" stopOpacity={0.2} /><stop offset="95%" stopColor="#526df5" stopOpacity={0.01} /></linearGradient></defs><CartesianGrid stroke="#eef0f5" vertical={false} /><XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fill: "#9299ab", fontSize: 11 }} tickFormatter={(value) => new Date(value).toLocaleDateString("en", { month: "short", day: "numeric" })} /><YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "#9299ab", fontSize: 11 }} /><Tooltip contentStyle={{ border: "1px solid #eef0f5", borderRadius: 10, boxShadow: "0 8px 24px #30395914", fontSize: 12 }} /><Area type="monotone" dataKey="count" name="Reports" stroke="#526df5" strokeWidth={2.5} fill="url(#areaFill)" activeDot={{ r: 5, strokeWidth: 0 }} /></AreaChart></ResponsiveContainer></div> : <EmptyChart title="Your trend line starts here">Complaint activity will show up once reports start coming in.</EmptyChart>}</section>
      <section className="panel breakdown-panel"><div className="chart-heading"><div><div className="section-kicker">WHAT NEEDS ATTENTION</div><h2>Issue categories</h2></div></div>{analytics?.by_category?.length ? <><div className="donut-wrap"><ResponsiveContainer width="100%" height={175}><PieChart><Pie data={analytics.by_category} dataKey="value" nameKey="name" innerRadius={53} outerRadius={73} paddingAngle={3} stroke="none">{analytics.by_category.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip contentStyle={{ border: "1px solid #eef0f5", borderRadius: 10, fontSize: 12 }} /></PieChart></ResponsiveContainer><div className="donut-total"><strong>{analytics.total}</strong><small>reports</small></div></div><div className="legend-grid">{analytics.by_category.slice(0, 6).map((item, index) => <div className="legend-item" key={item.name}><span style={{ background: COLORS[index % COLORS.length] }} />{item.name}<strong>{item.value}</strong></div>)}</div></> : <EmptyChart title="No categories to chart">Category insights appear as complaints are reported.</EmptyChart>}</section></div>
    <div className="analytics-grid analytics-grid-breakdown"><AnalyticsBreakdown eyebrow="WORKLOAD BY TEAM" title="Department load" items={analytics?.by_department || []} color="#39a98d" /><AnalyticsBreakdown eyebrow="HOW THINGS ARE MOVING" title="Status snapshot" items={analytics?.by_status || []} color="#8170d7" /></div>
  </>;
}
