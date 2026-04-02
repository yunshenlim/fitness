import { createClient } from '@supabase/supabase-js'

// 初始化 Supabase (Vercel 会自动读取你之前设的环境变量)
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

export default async function Home() {
  // 从 Supabase 获取最近的 5 条健身记录
  const { data: logs } = await supabase
    .from('fitness_logs')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(5)

  return (
    <main style={{ padding: '20px', backgroundColor: '#000', color: '#fff', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <header style={{ borderBottom: '1px solid #333', paddingBottom: '20px', marginBottom: '20px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>🚀 BIO-OS DASHBOARD</h1>
        <p style={{ color: '#888', fontSize: '14px' }}>Status: Operational | Location: BM, Penang</p>
      </header>

      <section>
        <h2 style={{ fontSize: '18px', marginBottom: '15px' }}>最近训练记录</h2>
        {logs?.map((log) => (
          <div key={log.id} style={{ background: '#111', padding: '15px', borderRadius: '8px', marginBottom: '10px', border: '1px solid #222' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#00ff88', fontWeight: 'bold' }}>{log.exercise.toUpperCase()}</span>
              <span style={{ color: '#666' }}>{new Date(log.created_at).toLocaleDateString()}</span>
            </div>
            <div style={{ marginTop: '5px', fontSize: '20px' }}>
              {log.weight}kg × {log.reps} reps × {log.sets} sets
            </div>
          </div>
        ))}
        {!logs?.length && <p style={{ color: '#444' }}>暂无数据，请通过 Telegram 发送指令记录。</p>}
      </section>

      <footer style={{ marginTop: '40px', color: '#333', fontSize: '12px', textAlign: 'center' }}>
        FSGE SYSTEM v1.0 | 2026.04
      </footer>
    </main>
  );
}
