// Global state
let currentPage = 1;
const perPage = 10; 

// DOM Elements
let expensesTbody;
let prevPageButton;
let nextPageButton;
let currentPageSpan;
let uploadCsvButton;
let channelSelect;
let csvFileInput;
let batchClassifyButton;
let visibilityFilterSelect;


// Fetch expenses from the API
async function fetchExpenses(page = 1) {
    if (typeof showGlobalLoader !== 'function' || typeof hideGlobalLoader !== 'function' || typeof fetchAPI !== 'function') {
        console.error("UI helpers or global fetchAPI not loaded!");
        if (typeof showToast === 'function') showToast("关键UI组件缺失，请刷新页面。(Critical UI components missing. Please refresh.)", "error");
        return;
    }
    showGlobalLoader();
    
    let apiParams = `page=${page}&per_page=${perPage}&sort_by=id&sort_order=DESC`;
    if (visibilityFilterSelect) { 
        const visibilityValue = visibilityFilterSelect.value;
        if (visibilityValue === 'visible') apiParams += '&is_hidden=0';
        else if (visibilityValue === 'hidden') apiParams += '&is_hidden=1';
    }

    try {
        const data = await fetchAPI(`/api/v1/expenses?${apiParams}`); 
        if (data) { 
            renderExpensesTable(data.expenses);
            updatePaginationControls(page, data.total_count);
            currentPage = page;
        } else {
             if (typeof showToast === 'function') showToast("未收到支出数据。(Received no data for expenses.)", "info");
             renderExpensesTable([]); 
             updatePaginationControls(page, 0);
        }
    } catch (error) {
        console.error('Error fetching expenses (error already shown by global fetchAPI):', error);
        renderExpensesTable([]); 
        updatePaginationControls(page, 0);
    } finally {
        hideGlobalLoader();
    }
}

// Render expenses data into the table
function renderExpensesTable(expenses) {
    if (!expensesTbody) return;
    expensesTbody.innerHTML = ''; 
    if (!expenses || expenses.length === 0) {
        const tr = expensesTbody.insertRow(); const td = tr.insertCell();
        td.colSpan = 13; td.textContent = '未找到支出记录。(No expenses found.)'; td.style.textAlign = 'center';
        return;
    }
    expenses.forEach(expense => {
        const tr = expensesTbody.insertRow();
        if (expense.is_hidden) tr.classList.add('hidden-row'); else tr.classList.remove('hidden-row');
        tr.insertCell().textContent = expense.id;
        tr.insertCell().textContent = new Date(expense.transaction_time).toLocaleString('zh-CN'); // Use Chinese locale for date
        tr.insertCell().textContent = expense.source_raw_description || expense.description_for_ai || '无 (N/A)';
        tr.insertCell().textContent = expense.amount;
        tr.insertCell().textContent = expense.channel || '无 (N/A)';
        tr.insertCell().textContent = expense.ai_suggestion_l1 || '无 (N/A)';
        tr.insertCell().textContent = expense.ai_suggestion_l2 || '无 (N/A)';
        const userL1Cell = tr.insertCell(); const userL1Input = document.createElement('input');
        userL1Input.type = 'text'; userL1Input.value = expense.category_l1 || '';
        userL1Input.placeholder = '一级分类 (L1)'; userL1Input.id = `userL1-${expense.id}`; userL1Cell.appendChild(userL1Input);
        const userL2Cell = tr.insertCell(); const userL2Input = document.createElement('input');
        userL2Input.type = 'text'; userL2Input.value = expense.category_l2 || '';
        userL2Input.placeholder = '二级分类 (L2)'; userL2Input.id = `userL2-${expense.id}`; userL2Cell.appendChild(userL2Input);
        tr.insertCell().textContent = expense.is_confirmed_by_user ? '是 (Yes)' : '否 (No)';
        const hiddenStatusCell = tr.insertCell(); hiddenStatusCell.textContent = expense.is_hidden ? '是 (Yes)' : '否 (No)';
        hiddenStatusCell.id = `hiddenStatus-${expense.id}`;
        const hideActionCell = tr.insertCell(); const hideCheckbox = document.createElement('input');
        hideCheckbox.type = 'checkbox'; hideCheckbox.classList.add('hide-expense-checkbox');
        hideCheckbox.dataset.expenseId = expense.id; hideCheckbox.checked = expense.is_hidden ? true : false;
        hideActionCell.appendChild(hideCheckbox);
        const actionsCell = tr.insertCell(); const classifyButton = document.createElement('button');
        classifyButton.textContent = 'AI分类 (Classify)'; classifyButton.classList.add('classify-btn');
        classifyButton.dataset.expenseId = expense.id; actionsCell.appendChild(classifyButton);
        const confirmButton = document.createElement('button');
        confirmButton.textContent = '确认分类 (Confirm)'; confirmButton.classList.add('confirm-btn');
        confirmButton.dataset.expenseId = expense.id; actionsCell.appendChild(confirmButton);
    });
}

// Update pagination controls
function updatePaginationControls(currentPageNum, totalCount) {
    if (!currentPageSpan || !prevPageButton || !nextPageButton) return;
    currentPageSpan.textContent = `页码 (Page): ${currentPageNum}`;
    prevPageButton.disabled = currentPageNum <= 1;
    nextPageButton.disabled = (currentPageNum * perPage) >= totalCount;
}

// Handle CSV file upload
async function handleCsvUpload() { 
    if (!csvFileInput || !channelSelect || !uploadCsvButton) return;
    const file = csvFileInput.files[0];
    const selectedChannel = channelSelect.value;
    if (!file) { showToast('请选择要上传的CSV文件。(Please select a CSV file to upload.)', 'error'); return; }
    if (!selectedChannel) { showToast('请选择渠道。(Please select a channel.)', 'error'); return; }
    
    const formData = new FormData();
    formData.append('file', file); formData.append('channel', selectedChannel);
    
    const originalButtonText = uploadCsvButton.textContent;
    uploadCsvButton.disabled = true; uploadCsvButton.textContent = '上传中... (Uploading...)';
    
    try {
        const result = await fetchAPI('/api/v1/import/csv', { method: 'POST', body: formData });
        if (result) { 
            showToast(`导入成功: ${result.import_summary?.successfully_imported || 0} 条记录已导入。(Import successful: ... records imported.)`, 'success');
            fetchExpenses(1); 
        } else {
            showToast('导入状态未知或未返回内容。(Import status unknown or no content returned.)', 'info');
        }
    } catch (error) { console.error('Error uploading CSV (error toast shown by fetchAPI):', error); }
    finally {
        uploadCsvButton.disabled = false; uploadCsvButton.textContent = originalButtonText;
    }
}

// Handle AI classification request for a single expense
async function handleClassifyExpense(buttonElement, expenseId) { 
    if (!buttonElement) return;
    const originalButtonText = buttonElement.textContent;
    buttonElement.disabled = true; buttonElement.textContent = '处理中... (Working...)';

    try {
        const updatedExpense = await fetchAPI(`/api/v1/expenses/${expenseId}/classify`, { method: 'POST' });
        if (updatedExpense) {
            const row = expensesTbody.querySelector(`button.classify-btn[data-expense-id="${expenseId}"]`)?.closest('tr');
            if (row) {
                row.cells[5].textContent = updatedExpense.ai_suggestion_l1 || '无 (N/A)';
                row.cells[6].textContent = updatedExpense.ai_suggestion_l2 || '无 (N/A)';
            } else { fetchExpenses(currentPage); } 
            showToast(`支出ID ${expenseId} 已分类。(Expense ID ${expenseId} classified.)`, 'success');
        }
    } catch (error) { console.error('Error classifying expense (error toast shown by fetchAPI):', error); }
    finally {
        buttonElement.disabled = false; buttonElement.textContent = originalButtonText;
    }
}

// Handle user confirmation of categories for a single expense
async function handleConfirmExpense(buttonElement, expenseId) { 
    if (!buttonElement) return;
    const userL1Input = document.getElementById(`userL1-${expenseId}`);
    const userL2Input = document.getElementById(`userL2-${expenseId}`);
    if (!userL1Input || !userL2Input) { showToast(`支出ID ${expenseId} 的输入框未找到。(Input fields for expense ID ${expenseId} not found.)`, 'error'); return; }
    const userL1 = userL1Input.value.trim(); const userL2 = userL2Input.value.trim();
    if (!userL1 || !userL2) { showToast('用户确认时，一级和二级分类不能为空。(User L1 and L2 categories cannot be empty for confirmation.)', 'error'); return; }
    
    const originalButtonText = buttonElement.textContent;
    buttonElement.disabled = true; buttonElement.textContent = '保存中... (Saving...)';

    try {
        const updatedExpense = await fetchAPI(`/api/v1/expenses/${expenseId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category_l1: userL1, category_l2: userL2 }) });
        if (updatedExpense) {
            const row = expensesTbody.querySelector(`button.confirm-btn[data-expense-id="${expenseId}"]`)?.closest('tr');
            if (row) {
                userL1Input.value = updatedExpense.category_l1 || ''; userL2Input.value = updatedExpense.category_l2 || '';
                row.cells[9].textContent = updatedExpense.is_confirmed_by_user ? '是 (Yes)' : '否 (No)';
            } else { fetchExpenses(currentPage); }
            showToast(`支出ID ${expenseId} 的分类已确认。(Expense ID ${expenseId} categories confirmed.)`, 'success');
        }
    } catch (error) { console.error('Error confirming expense categories (error toast shown by fetchAPI):', error); }
    finally {
        buttonElement.disabled = false; buttonElement.textContent = originalButtonText;
    }
}

// Handle Batch AI Classification
async function handleBatchClassify() { 
    if (!batchClassifyButton) return;
    const originalButtonText = batchClassifyButton.textContent;
    batchClassifyButton.disabled = true; batchClassifyButton.textContent = '处理中... (Processing...)';

    const requestPayload = {}; 
    try {
        const summary = await fetchAPI('/api/v1/ai/batch_classify_expenses', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestPayload) });
        if (summary) {
            let messageText = `批量分类完成: 匹配总数: ${summary.total_matching_criteria || 0}, 本批处理: ${summary.processed_in_this_batch || 0}, 成功分类: ${summary.successfully_classified || 0}, 分类失败: ${summary.failed_to_classify || 0}.`;
            if (summary.message && summary.message !== "No expenses to process.") messageText += ` 服务器消息: ${summary.message}`;
            else if (summary.message === "No expenses to process." && summary.processed_in_this_batch === 0) messageText = "批量分类: 未找到符合条件的新支出记录。";
            showToast(messageText, 'success', 10000); 
            fetchExpenses(1); 
        }
    } catch (error) { console.error("Batch classification failed (error toast shown by fetchAPI):", error); }
    finally {
        batchClassifyButton.disabled = false; batchClassifyButton.textContent = originalButtonText;
    }
}

// Handle Hide Expense Checkbox Change
async function handleHideExpenseToggle(checkboxElement, expenseId) {
    if (!checkboxElement) return;
    const isHidden = checkboxElement.checked;
    checkboxElement.disabled = true; 

    try {
        await fetchAPI(`/api/v1/expenses/${expenseId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_hidden: isHidden }) });
        showToast(`支出ID ${expenseId} 的隐藏状态已更新为: ${isHidden ? '隐藏 (Hidden)' : '可见 (Visible)'}.`, 'success');
        
        const row = checkboxElement.closest('tr');
        const hiddenStatusCell = document.getElementById(`hiddenStatus-${expenseId}`);
        if (row) { if (isHidden) row.classList.add('hidden-row'); else row.classList.remove('hidden-row'); }
        if (hiddenStatusCell) hiddenStatusCell.textContent = isHidden ? '是 (Yes)' : '否 (No)';

        const currentVisibilityFilter = visibilityFilterSelect ? visibilityFilterSelect.value : 'all';
        if ((currentVisibilityFilter === 'visible' && isHidden) || (currentVisibilityFilter === 'hidden' && !isHidden)) {
            fetchExpenses(currentPage); 
        }
    } catch (error) {
        showToast(`更新支出ID ${expenseId} 的隐藏状态失败: ${error.message}`, 'error');
        checkboxElement.checked = !isHidden; 
    } finally {
        checkboxElement.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    expensesTbody = document.getElementById('expenses-tbody');
    prevPageButton = document.getElementById('prev-page');
    nextPageButton = document.getElementById('next-page');
    currentPageSpan = document.getElementById('current-page');
    uploadCsvButton = document.getElementById('upload-csv-button');
    channelSelect = document.getElementById('channel-select');
    csvFileInput = document.getElementById('csv-file-input');
    batchClassifyButton = document.getElementById('batch-classify-button');
    visibilityFilterSelect = document.getElementById('visibility-filter-select'); 

    if (expensesTbody && typeof fetchExpenses === 'function' && typeof showGlobalLoader === 'function') { 
        fetchExpenses(currentPage);
    } else {
        console.error("Essential components for expenses page not found or UI helpers not loaded.");
        if (typeof showToast === 'function') showToast("错误：页面组件初始化失败。(Error initializing page components.)", "error");
    }
    
    if (uploadCsvButton) uploadCsvButton.addEventListener('click', handleCsvUpload);
    if (prevPageButton) prevPageButton.addEventListener('click', () => { if (currentPage > 1) fetchExpenses(currentPage - 1); });
    if (nextPageButton) nextPageButton.addEventListener('click', () => fetchExpenses(currentPage + 1));
    if (batchClassifyButton) batchClassifyButton.addEventListener('click', handleBatchClassify);
    
    if (visibilityFilterSelect) {
        visibilityFilterSelect.addEventListener('change', () => {
            currentPage = 1; 
            fetchExpenses(currentPage);
        });
    }

    if (expensesTbody) {
        expensesTbody.addEventListener('click', (event) => {
            const target = event.target;
            if (target.classList.contains('classify-btn') && target.dataset.expenseId) {
                handleClassifyExpense(target, target.dataset.expenseId);
            } else if (target.classList.contains('confirm-btn') && target.dataset.expenseId) {
                handleConfirmExpense(target, target.dataset.expenseId);
            } 
        });
        expensesTbody.addEventListener('change', (event) => {
            const target = event.target;
            if (target.classList.contains('hide-expense-checkbox') && target.dataset.expenseId) {
                handleHideExpenseToggle(target, target.dataset.expenseId);
            }
        });
    }
});
