#!/usr/bin/env python3
import os, datetime

def generate():
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    build = os.environ.get('BUILD_NUMBER', 'Unknown')
    html = f"""<html><head><title>DevSecOps Report</title></head><body>
    <h1>DevSecOps Security Report</h1>
    <p>Generated: {now}</p><p>Build: #{build}</p>
    <h2>Summary</h2>
    <ul><li>SAST: see SonarQube</li><li>Container: see trivy-report.json</li><li>DAST: see zap-report.json</li></ul>
    </body></html>"""
    with open('security-report.html','w') as f:
        f.write(html)
    print('Security report generated: security-report.html')

if __name__ == '__main__':
    generate()
