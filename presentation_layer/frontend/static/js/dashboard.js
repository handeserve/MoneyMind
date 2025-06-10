// In dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    // Check if Chart and UI helpers are loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded! Please check the CDN link in index.html.');
        const appContent = document.getElementById('app-content');
        if (appContent) appContent.innerHTML = '<p style="color: red; font-weight: bold;">错误：Chart.js库加载失败，图表无法显示。(Error: Chart.js library failed to load. Charts cannot be displayed.)</p>' + appContent.innerHTML;
        return;
    }
    if (typeof showGlobalLoader === 'undefined' || typeof hideGlobalLoader === 'undefined' || 
        typeof showToast === 'undefined' || typeof fetchAPI === 'undefined') { 
        console.error('ui_helpers.js is not loaded or is missing functions! Please check the script link in index.html.');
        const appContent = document.getElementById('app-content');
        if (appContent) appContent.innerHTML = '<p style="color: red; font-weight: bold;">错误：必要的UI辅助功能加载失败，页面可能无法正常工作。(Error: Essential UI helper functions failed to load. Page may not work correctly.)</p>' + appContent.innerHTML;
        return;
    }
    console.log("Dashboard.js loaded. Chart.js version:", Chart.version);

    // Global Chart Instances Store
    let charts = {};

    // DOM Elements
    const dateRangeSelect = document.getElementById('date-range-select');
    const granularitySelect = document.getElementById('granularity-select');
    const totalExpensesValue = document.getElementById('total-expenses-value');
    const avgDailyExpensesValue = document.getElementById('avg-daily-expenses-value');

    function formatDate(date) { 
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function getDateRange() {
        const selectedRange = dateRangeSelect.value;
        const today = new Date();
        let startDate = new Date();
        let endDate = new Date(today); 

        switch (selectedRange) {
            case 'last_7_days': startDate.setDate(today.getDate() - 6); break;
            case 'last_30_days': startDate.setDate(today.getDate() - 29); break;
            case 'current_month':
                startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                break;
            case 'last_month':
                startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                endDate = new Date(today.getFullYear(), today.getMonth(), 0);
                break;
            default: startDate.setDate(today.getDate() - 29);
        }
        return { startDate: formatDate(startDate), endDate: formatDate(endDate) };
    }

    const defaultChartOptions = { 
        responsive: true, maintainAspectRatio: false,
        plugins: {
            legend: { position: 'top' },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) label += ': ';
                        if (context.parsed.y !== null) label += new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(context.parsed.y); // Changed to zh-CN
                        else if (context.parsed !== null && typeof context.parsed === 'number') label += new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(context.parsed); // Changed to zh-CN
                        return label;
                    }
                }
            }
        }
    };
    const CHART_COLORS = [ 
        'rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)', 'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)',
        'rgba(255, 99, 71, 0.7)',  'rgba(60, 179, 113, 0.7)', 'rgba(238, 130, 238, 0.7)',
        'rgba(106, 90, 205, 0.7)', 'rgba(255, 127, 80, 0.7)', 'rgba(0, 206, 209, 0.7)'
    ];

    function renderChart(canvasId, type, data, options, chartName) {
        if (charts[chartName]) charts[chartName].destroy();
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`Canvas element with ID '${canvasId}' not found.`);
            showToast(`图表容器 '${canvasId}' 未找到。(Chart container '${canvasId}' not found.)`, 'error'); 
            return;
        }
        charts[chartName] = new Chart(ctx, { type, data, options: { ...defaultChartOptions, ...options } });
    }

    async function fetchSummaryStats(startDate, endDate, showLoaderPerFetch = false) {
        try {
            const data = await fetchAPI(`/api/v1/dashboard/summary_stats?start_date=${startDate}&end_date=${endDate}`, {}, showLoaderPerFetch);
            if (totalExpensesValue) {
                totalExpensesValue.textContent = `¥${parseFloat(data.total_expenses || 0).toFixed(2)}`;
            } else { console.warn("totalExpensesValue element not found in DOM."); }
            if (avgDailyExpensesValue) {
                avgDailyExpensesValue.textContent = `¥${parseFloat(data.average_daily_expenses || 0).toFixed(2)}`;
            } else { console.warn("avgDailyExpensesValue element not found in DOM."); }
        } catch (error) {
            console.error('Error fetching summary stats (handled by fetchAPI):', error);
            if (totalExpensesValue) totalExpensesValue.textContent = '错误 (Error)';
            if (avgDailyExpensesValue) avgDailyExpensesValue.textContent = '错误 (Error)';
            // showToast is called by fetchAPI
        }
    }

    async function fetchChannelDistribution(startDate, endDate, showLoaderPerFetch = false) {
        try {
            const data = await fetchAPI(`/api/v1/dashboard/channel_distribution?start_date=${startDate}&end_date=${endDate}`, {}, showLoaderPerFetch);
            const canvasElement = document.getElementById('channelPieChart');
            if (!canvasElement) { console.warn("channelPieChart canvas element not found."); if (data && data.length === 0) showToast('此期间无渠道分布数据。(No data for channel distribution.)', 'info'); return; }
            if (!data || data.length === 0) {
                showToast('此期间无渠道分布数据。(No data for channel distribution in this period.)', 'info');
                if (charts['channelChart']) { charts['channelChart'].destroy(); delete charts['channelChart']; }
                canvasElement.style.display = 'none'; return;
            }
            canvasElement.style.display = 'block';
            const chartData = { labels: data.map(item => item.channel), datasets: [{ label: '渠道支出 (Spending by Channel)', data: data.map(item => item.total_amount), backgroundColor: CHART_COLORS, hoverOffset: 4 }] };
            renderChart('channelPieChart', 'doughnut', chartData, { plugins: { title: { display: true, text: '渠道支出占比 (Spending by Channel)' } } }, 'channelChart');
        } catch (error) { console.error('Error fetching channel distribution (handled by fetchAPI):', error); }
    }

    async function fetchExpenseTrend(startDate, endDate, granularity, showLoaderPerFetch = false) {
        try {
            const data = await fetchAPI(`/api/v1/dashboard/expense_trend?start_date=${startDate}&end_date=${endDate}&granularity=${granularity}`, {}, showLoaderPerFetch);
            const canvasElement = document.getElementById('expenseTrendLineChart');
            if (!canvasElement) { console.warn("expenseTrendLineChart canvas element not found."); if (data && data.length === 0) showToast('此期间无支出趋势数据。(No data for expense trend.)', 'info'); return; }
            if (!data || data.length === 0) {
                showToast('此期间无支出趋势数据。(No data for expense trend in this period.)', 'info');
                if (charts['trendChart']) { charts['trendChart'].destroy(); delete charts['trendChart']; }
                canvasElement.style.display = 'none'; return;
            }
            canvasElement.style.display = 'block';
            const chartData = { labels: data.map(item => item.date_period), datasets: [{ label: `支出趋势 (${granularity}) (Expense Trend (${granularity}))`, data: data.map(item => item.total_amount), fill: false, borderColor: CHART_COLORS[0], tension: 0.1 }] };
            renderChart('expenseTrendLineChart', 'line', chartData, { plugins: { title: { display: true, text: `支出趋势 (${granularity}) (Expense Trend (${granularity}))` } }, scales: { y: { beginAtZero: true } } }, 'trendChart');
        } catch (error) { console.error('Error fetching expense trend (handled by fetchAPI):', error); }
    }

    async function fetchCategorySpending(startDate, endDate, showLoaderPerFetch = false) {
        try {
            const data = await fetchAPI(`/api/v1/dashboard/category_spending?start_date=${startDate}&end_date=${endDate}`, {}, showLoaderPerFetch);
            const canvasElement = document.getElementById('categoryBarChart');
            if (!canvasElement) { console.warn("categoryBarChart canvas element not found."); if (data && data.length === 0) showToast('此期间无分类支出数据。(No data for category spending.)', 'info'); return; }
            if (!data || data.length === 0) {
                showToast('此期间无分类支出数据。(No data for category spending in this period.)', 'info');
                if (charts['categoryChart']) { charts['categoryChart'].destroy(); delete charts['categoryChart']; }
                canvasElement.style.display = 'none'; return;
            }
            canvasElement.style.display = 'block';
            const chartData = { labels: data.map(item => item.category_l1), datasets: [{ label: '一级分类支出 (Spending by Category (L1))', data: data.map(item => item.total_amount), backgroundColor: CHART_COLORS, borderColor: CHART_COLORS.map(color => color.replace('0.7', '1')), borderWidth: 1 }] };
            renderChart('categoryBarChart', 'bar', chartData, { indexAxis: 'y', plugins: { title: { display: true, text: '一级分类支出 (Spending by L1 Category)' } }, scales: { x: { beginAtZero: true } } }, 'categoryChart');
        } catch (error) { console.error('Error fetching category spending (handled by fetchAPI):', error); }
    }

    async function updateDashboard() { 
        showGlobalLoader(); 
        const { startDate, endDate } = getDateRange();
        const granularity = granularitySelect.value;
        console.log(`Updating dashboard for: ${startDate} to ${endDate}, Granularity: ${granularity}`); // Keep for debugging

        try {
            await Promise.all([
                fetchSummaryStats(startDate, endDate, false),
                fetchChannelDistribution(startDate, endDate, false),
                fetchExpenseTrend(startDate, endDate, granularity, false),
                fetchCategorySpending(startDate, endDate, false)
            ]);
            showToast('仪表盘数据已更新！(Dashboard updated successfully!)', 'success');
        } catch (error) {
            console.error("Error updating dashboard components (Promise.all):", error);
            showToast('更新部分仪表盘组件失败。(Failed to update some dashboard components.)', 'error');
        } finally {
            hideGlobalLoader(); 
        }
    }

    if (dateRangeSelect && granularitySelect && totalExpensesValue && avgDailyExpensesValue) {
        updateDashboard(); 
        dateRangeSelect.addEventListener('change', updateDashboard);
        granularitySelect.addEventListener('change', updateDashboard);
    } else {
        console.error("One or more essential dashboard DOM elements are missing. Dashboard cannot initialize.");
        showToast("错误：缺少必要的页面元素，仪表盘无法加载。(Error: Essential page elements missing. Dashboard cannot load.)", "error");
    }
});

// 显示提示信息
function showToast(message, type = 'info') {
    // 获取所有现有的提示
    const existingToasts = document.querySelectorAll('.toast');
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    
    // 创建新的提示元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    // 添加到容器
    toastContainer.appendChild(toast);

    // 触发重排以启动动画
    toast.offsetHeight;

    // 显示提示
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // 5秒后自动消失
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
            // 如果容器为空，也移除容器
            if (toastContainer.children.length === 0) {
                toastContainer.remove();
            }
        }, 300);
    }, 5000);
}

// 创建提示容器
function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// 加载仪表板数据
async function loadDashboardData() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    try {
        // 加载汇总数据
        const summaryResponse = await fetch(`/api/v1/dashboard/summary?start_date=${startDate}&end_date=${endDate}`);
        if (!summaryResponse.ok) {
            throw new Error('获取汇总数据失败');
        }
        const summaryData = await summaryResponse.json();
        updateSummaryStats(summaryData);

        // 加载分类支出数据
        const categoryResponse = await fetch(`/api/v1/dashboard/category_spending?start_date=${startDate}&end_date=${endDate}`);
        if (!categoryResponse.ok) {
            throw new Error('获取分类支出数据失败');
        }
        const categoryData = await categoryResponse.json();
        updateCategoryChart(categoryData);

        // 加载渠道支出数据
        const channelResponse = await fetch(`/api/v1/dashboard/channel_spending?start_date=${startDate}&end_date=${endDate}`);
        if (!channelResponse.ok) {
            throw new Error('获取渠道支出数据失败');
        }
        const channelData = await channelResponse.json();
        updateChannelChart(channelData);

        // 加载支出趋势数据
        const trendResponse = await fetch(`/api/v1/dashboard/expense_trend?start_date=${startDate}&end_date=${endDate}&granularity=daily`);
        if (!trendResponse.ok) {
            throw new Error('获取支出趋势数据失败');
        }
        const trendData = await trendResponse.json();
        updateTrendChart(trendData);

        showToast('数据加载成功', 'success');
    } catch (error) {
        console.error('加载数据失败:', error);
        showToast(error.message || '加载数据失败，请稍后重试', 'error');
    }
}

// 更新汇总统计
function updateSummaryStats(data) {
    document.getElementById('totalExpenses').textContent = formatCurrency(data.total_expense);
    document.getElementById('avgDailyExpense').textContent = formatCurrency(data.avg_expense);
    document.getElementById('maxExpense').textContent = formatCurrency(data.max_expense);
    document.getElementById('minExpense').textContent = formatCurrency(data.min_expense);
}

// 更新分类支出图表
function updateCategoryChart(data) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    if (window.categoryChart) {
        window.categoryChart.destroy();
    }
    window.categoryChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.map(item => item.category_l1 || '未分类'),
            datasets: [{
                data: data.map(item => Math.abs(item.total_expense)),
                backgroundColor: generateColors(data.length)
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right'
                },
                title: {
                    display: true,
                    text: '支出分类分布'
                }
            }
        }
    });
}

// 更新渠道支出图表
function updateChannelChart(data) {
    const ctx = document.getElementById('channelChart').getContext('2d');
    if (window.channelChart) {
        window.channelChart.destroy();
    }
    window.channelChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.channel),
            datasets: [{
                label: '支出金额',
                data: data.map(item => Math.abs(item.total_expense)),
                backgroundColor: generateColors(data.length)
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: '支付渠道分布'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: value => formatCurrency(value)
                    }
                }
            }
        }
    });
}

// 更新支出趋势图表
function updateTrendChart(data) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    if (window.trendChart) {
        window.trendChart.destroy();
    }
    window.trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(item => item.date),
            datasets: [{
                label: '日支出',
                data: data.map(item => Math.abs(item.daily_expense)),
                borderColor: '#2196f3',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: '支出趋势'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: value => formatCurrency(value)
                    }
                }
            }
        }
    });
}

// 生成随机颜色
function generateColors(count) {
    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(`hsl(${(i * 360) / count}, 70%, 60%)`);
    }
    return colors;
}

// 格式化货币
function formatCurrency(value) {
    return new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: 'CNY'
    }).format(value);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 设置默认日期范围（最近30天）
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    document.getElementById('startDate').value = startDate.toISOString().split('T')[0];
    document.getElementById('endDate').value = endDate.toISOString().split('T')[0];

    // 加载初始数据
    loadDashboardData();

    // 添加日期选择事件监听
    document.getElementById('startDate').addEventListener('change', loadDashboardData);
    document.getElementById('endDate').addEventListener('change', loadDashboardData);
});
