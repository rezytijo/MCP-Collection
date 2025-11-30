import asyncio
import json
from document_server import document_generate_word

async def main():
    placeholders = {
        "{nomor}": "002",
        "{bulan}": "11",
        "{nama_aplikasi}": "testphp.vulnweb.com",
        "{repositori}": "https://github.com/testphp/vulnweb",
        "{satuan_kerja}": "Kementerian Komunikasi dan Informatika",
        "{pic_nip_hp}": "John Doe / 123456789 / 08123456789",
        "{ip_address}": "44.228.249.3",
        "{sub_domain}": "testphp.vulnweb.com",
        "{pentester}": "MCP Kali Scanner",
        "{domain}": "vulnweb.com",
        "{executive_summary}": "Penilaian kerentanan aplikasi web testphp.vulnweb.com mengungkapkan celah keamanan kritis berupa SQL Injection yang dapat dieksploitasi untuk mengakses database sensitif. Temuan ini berdasarkan pemindaian menggunakan tools Nmap, Nikto, dan SQLMap.",
        "{scope}": "Penilaian dilakukan pada aplikasi web testphp.vulnweb.com yang terletak di alamat IP 44.228.249.3. Scope mencakup pemindaian port, deteksi kerentanan web umum, dan pengujian SQL injection pada parameter yang ditemukan.",
        "{methodology}": "Penilaian dilakukan menggunakan tools keamanan dari Kali Linux melalui MCP:\n- Nmap untuk pemindaian port dan layanan\n- Nikto untuk deteksi kerentanan web umum\n- SQLMap untuk pengujian SQL injection\n- DNS enumeration untuk informasi domain\n\nTools digunakan secara otomatis melalui MCP server.",
        "{findings}": "| No | Vulnerability | Severity | Location | Description | Impact | Recommendation |\n|----|--------------|----------|----------|-------------|--------|----------------|\n| 1 | SQL Injection | High | listproducts.php?cat= | Parameter 'cat' rentan terhadap berbagai jenis SQL injection (boolean-based, error-based, time-based, UNION). | Attacker dapat dump database, modify data, atau execute arbitrary commands. | Implement prepared statements and input validation. |\n| 2 | Missing Security Headers | Medium | Global | Aplikasi tidak menggunakan header keamanan seperti X-Frame-Options dan X-Content-Type-Options. | Meningkatkan risiko clickjacking dan MIME sniffing attacks. | Add security headers in web server configuration. |\n| 3 | Insecure Cross-Domain Policy | Low | crossdomain.xml | File crossdomain.xml mengandung wildcard entries yang tidak aman. | Memungkinkan cross-domain requests yang tidak diinginkan. | Restrict cross-domain policies to trusted domains only. |",
        "{recommendations}": "1. **Implementasi Prepared Statements**: Gunakan prepared statements untuk semua query database untuk mencegah SQL injection.\n\n2. **Input Validation dan Sanitization**: Validasi dan sanitize semua input user, termasuk penggunaan whitelist untuk karakter yang diizinkan.\n\n3. **Add Security Headers**: Implementasikan header keamanan seperti X-Frame-Options, X-Content-Type-Options, dan Content Security Policy.\n\n4. **Restrict Cross-Domain Policies**: Batasi crossdomain.xml dan clientaccesspolicy.xml hanya untuk domain terpercaya.\n\n5. **Update Dependencies**: Pastikan semua library dan framework diperbarui ke versi terbaru yang aman.\n\n6. **Regular Security Audits**: Lakukan penilaian keamanan berkala menggunakan automated tools dan manual testing.",
        "{image1}": "/app/images/vapt_chart_real.png"
    }

    result = await document_generate_word(
        content="",
        template="VAPT Report.docx",
        output_name="002_11_KCSIRT_11_2025_VAPT_Report_testphp_vulnweb_com_real_scan.docx",
        placeholders=json.dumps(placeholders)
    )

    print("Document generated:", result)

if __name__ == "__main__":
    asyncio.run(main())