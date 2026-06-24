function initAdminCharts(chartData) {
    const isDark = document.documentElement.classList.contains('dark');
    Chart.defaults.color = isDark ? '#9CA3AF' : '#4B5563';
    Chart.defaults.borderColor = isDark ? '#374151' : '#E5E7EB';
    Chart.defaults.font.family = 'Inter, sans-serif';

    // Лінійний графік реєстрацій
    new Chart(document.getElementById('lineChart'), {
        type: 'line',
        data: {
            labels: chartData.line.labels,
            datasets: [
                {
                    label: 'Користувачі',
                    data: chartData.line.users,
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'СТО',
                    data: chartData.line.stations,
                    borderColor: '#3B82F6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    // Кругова діаграма розподілу за містами
    new Chart(document.getElementById('donutChart'), {
        type: 'doughnut',
        data: {
            labels: chartData.donut.labels,
            datasets: [{
                data: chartData.donut.data,
                backgroundColor: ['#10B981', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6'],
                borderWidth: 0
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    // Стовпчастий графік розподілу оцінок
    new Chart(document.getElementById('barChart'), {
        type: 'bar',
        data: {
            labels: ['1 зірка', '2 зірки', '3 зірки', '4 зірки', '5 зірок'],
            datasets: [{
                label: 'Кількість відгуків',
                data: chartData.bar.data,
                backgroundColor: '#10B981',
                borderRadius: 4
            }]
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
        }
    });
}
