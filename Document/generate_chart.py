import matplotlib.pyplot as plt

# Data from VAPT findings
vulnerabilities = {
    'SQL Injection': 2,
    'XSS': 1
}

labels = list(vulnerabilities.keys())
sizes = list(vulnerabilities.values())

# Create pie chart
plt.figure(figsize=(8, 6))
plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
plt.title('Vulnerabilities Found in testphp.vulnweb.com')
plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

# Save the chart
plt.savefig('/app/images/vapt_chart.png')
print("Chart generated: /app/images/vapt_chart.png")