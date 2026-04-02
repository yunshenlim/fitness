import { createClient } from '@supabase/supabase-js'

// 初始化 Supabase 客户端
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

export default async function Home() {
  // 从数据库抓取最近 10 条健身记录
  const { data: logs, error } = await supabase
    .from('fitness_logs') // 确保你的表名是这个
    .select('*')
    .order('created_at', { ascending: false })
    .limit(10)

  return (
    <main style={{ padding: '30px', backgroundColor: '#000', color: '#fff', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <header style={{ borderBottom: '1px solid #333', marginBottom: '30px', paddingBottom: '10px' }}>
        <h1 style={{ fontSize: '28px', letterSpacing: '-1px' }}>🧬 BIO-OS DASHBOARD</h1>
        <p style={{ color: '#666' }}>Location: Bukit Mertajam | Status: Live</p>
      </header>

      <div style={{ display: 'grid', gap: '15px' }}>
        {logs?.map((log) => (
          <div key={log.id} style={{ border: '1px solid #222', padding: '20px', borderRadius: '12px', background: '#0a0a0a' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#00ff88', fontWeight: 'bold' }}>
              <span>{log.exercise.toUpperCase()}</span>
              <span style={{ color: '#444' }}>{new Date(log.created_at).toLocaleTimeString()}</span>
            </div>
            <div style={{ fontSize: '24px', marginTop: '10px' }}>
              {log.weight}kg <span style={{ color: '#444', fontSize: '16px' }}>×</span> {log.sets} <span style={{ color: '#444', fontSize: '16px' }}>×</span> {log.reps}
            </div>
          </div>
        ))}

        {(!logs || logs.length === 0) && (
          <div style={{ color: '#444', textAlign: 'center', padding: '50px' }}>
            等待数据同步... 请在 Telegram 发送指令。
          </div>
        )}
      </div>
    </main>
  )
}
