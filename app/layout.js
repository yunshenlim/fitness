export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ 
        margin: 0, 
        backgroundColor: '#000', 
        color: '#fff', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontFamily: 'sans-serif'
      }}>
        {children}
      </body>
    </html>
  )
}
