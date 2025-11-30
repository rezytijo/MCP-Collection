#!/usr/bin/env python3

import json
import sys
import os

# Add the host directory to path so we can import
sys.path.insert(0, '/app/host')

from document_server import document_generate_word

async def main():
    placeholders = {
        "{nomor}": "001",
        "{bulan}": "11",
        "{nama_aplikasi}": "testphp.vulnweb.com",
        "{repositori}": "https://github.com/testphp/vulnweb",
        "{satuan_kerja}": "Kementerian Komunikasi dan Informatika",
        "{pic_nip_hp}": "John Doe / 123456789 / 08123456789",
        "{ip_address}": "185.53.178.9",
        "{sub_domain}": "testphp.vulnweb.com",
        "{pentester}": "AI Scanner via MCP",
        "{domain}": "testphp.vulnweb.com",
        "{executive_summary}": "Penilaian kerentanan aplikasi web testphp.vulnweb.com mengungkapkan beberapa celah keamanan kritis termasuk SQL Injection dan Cross-Site Scripting (XSS). Temuan ini menunjukkan bahwa aplikasi rentan terhadap serangan injeksi dan skrip lintas situs yang dapat dieksploitasi oleh penyerang untuk mengakses data sensitif atau mengeksekusi kode berbahaya.",
        "{scope}": "Penilaian dilakukan pada aplikasi web testphp.vulnweb.com yang terletak di alamat IP 185.53.178.9. Scope mencakup semua halaman publik dan fungsi yang dapat diakses tanpa autentikasi, termasuk halaman kategori produk, guestbook, dan form login.",
        "{methodology}": "Penilaian dilakukan menggunakan teknik manual testing dengan browser automation. Metode yang digunakan meliputi:\n- Testing parameter URL untuk SQL Injection\n- Testing form input untuk XSS\n- Testing authentication bypass\n\nTools yang digunakan: Browser automation via MCP tools untuk simulasi interaksi pengguna.",
        "{findings}": "| No | Vulnerability | Severity | Location | Description | Impact | Recommendation |\n|----|--------------|----------|----------|-------------|--------|----------------|\n| 1 | SQL Injection | High | listproducts.php?cat= | Parameter 'cat' rentan terhadap SQL injection. Input malicious dapat mengubah query database. | Attacker dapat dump database, modify data, atau execute arbitrary commands. | Implement prepared statements and input validation. |\n| 2 | Cross-Site Scripting (XSS) | Medium | guestbook.php | Form guestbook tidak sanitize input, memungkinkan injeksi script. | Attacker dapat execute JavaScript di browser victim, steal cookies, atau deface site. | Sanitize all user inputs and implement Content Security Policy. |\n| 3 | SQL Injection | High | login.php | Form login rentan terhadap SQL injection di field username. | Attacker dapat bypass authentication dan access accounts. | Use parameterized queries and escape special characters. |",
        "{recommendations}": "1. **Implementasi Prepared Statements**: Gunakan prepared statements untuk semua query database untuk mencegah SQL injection.\n\n2. **Input Validation dan Sanitization**: Validasi dan sanitize semua input user, termasuk penggunaan whitelist untuk karakter yang diizinkan.\n\n3. **Content Security Policy (CSP)**: Implementasikan CSP untuk mencegah XSS attacks.\n\n4. **Regular Security Audits**: Lakukan penilaian keamanan berkala menggunakan automated tools dan manual testing.\n\n5. **Update Dependencies**: Pastikan semua library dan framework diperbarui ke versi terbaru yang aman.\n\n6. **Error Handling**: Jangan expose error messages yang mengandung informasi sensitif ke users.",
        "{image1}": "/app/images/vapt_chart.png"
    }
    
    result = await document_generate_word(
        content="",
        template="VAPT Report.docx",
        output_name="001_11_KCSIRT_11_2025_VAPT_Report_testphp_vulnweb_com_final_clean.docx",
        placeholders=json.dumps(placeholders)
    )
    
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())