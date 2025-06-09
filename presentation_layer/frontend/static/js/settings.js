// In settings.js
document.addEventListener('DOMContentLoaded', function() {
    // Ensure UI helpers are loaded
    if (typeof showGlobalLoader !== 'function' || typeof hideGlobalLoader !== 'function' || 
        typeof showToast !== 'function' || typeof fetchAPI !== 'function') { 
        console.error('ui_helpers.js is not loaded or is missing functions! Page may not work correctly.');
        const appContent = document.getElementById('app-content');
        if (appContent) appContent.innerHTML = '<p style="color: red; font-weight: bold;">错误：必要的UI辅助功能加载失败，请刷新或检查控制台。(Error: Essential UI helper functions failed to load. Please refresh or check console.)</p>' + appContent.innerHTML;
        return;
    }
    console.log("Settings.js loaded.");

    // DOM Elements
    const defaultLlmServiceSelect = document.getElementById('default-llm-service-select');
    const llmServicesConfigsContainer = document.getElementById('llm-services-configs-container');
    const saveAIModelConfigButton = document.getElementById('save-ai-model-config-button');
    const promptTemplatesContainer = document.getElementById('prompt-templates-container');
    const savePromptsButton = document.getElementById('save-prompts-button');
    const categoriesListContainer = document.getElementById('categories-list-container');
    const newL1CategoryNameInput = document.getElementById('new-l1-category-name');
    const addL1CategoryButton = document.getElementById('add-l1-category-button');

    async function loadAIConfig(showLoader = true) { 
        if (showLoader) showGlobalLoader();
        try {
            const configData = await fetchAPI('/api/v1/settings/ai_config', {}, !showLoader); // Pass !showLoader
            
            if (defaultLlmServiceSelect && configData && configData.llm_services) {
                defaultLlmServiceSelect.innerHTML = ''; 
                Object.keys(configData.llm_services).forEach(serviceName => {
                    const option = document.createElement('option');
                    option.value = serviceName; option.textContent = serviceName;
                    if (serviceName === configData.default_llm_service) option.selected = true;
                    defaultLlmServiceSelect.appendChild(option);
                });
            }

            if (llmServicesConfigsContainer && configData && configData.llm_services) {
                llmServicesConfigsContainer.innerHTML = '';
                for (const [serviceName, serviceDetails] of Object.entries(configData.llm_services)) {
                    const fieldset = document.createElement('fieldset');
                    fieldset.className = 'service-config-fieldset'; fieldset.dataset.serviceName = serviceName;
                    fieldset.innerHTML = `
                        <legend>${serviceName} 配置 (Configuration)</legend>
                        <div><label for="${serviceName}-api-key">API密钥 (API Key):</label><input type="password" id="${serviceName}-api-key" placeholder="******** (如需更新请输入 / Update if changing)"></div>
                        <div><label for="${serviceName}-model-name">模型名称 (Model Name):</label><input type="text" id="${serviceName}-model-name" value="${serviceDetails.model_params?.model_name || ''}" placeholder="例如 deepseek-chat (e.g., deepseek-chat)"></div>
                        <div><label for="${serviceName}-temperature">温度 (Temperature) (0.0-2.0):</label><input type="number" id="${serviceName}-temperature" step="0.1" min="0" max="2" value="${serviceDetails.model_params?.temperature || ''}"></div>
                        <div><label for="${serviceName}-max-tokens">最大令牌数 (Max Tokens):</label><input type="number" id="${serviceName}-max-tokens" step="1" min="1" value="${serviceDetails.model_params?.max_tokens || ''}"></div>
                    `;
                    llmServicesConfigsContainer.appendChild(fieldset);
                }
            }

            if (promptTemplatesContainer && configData && configData.prompt_templates) {
                promptTemplatesContainer.innerHTML = ''; 
                configData.prompt_templates.forEach(prompt => {
                    const div = document.createElement('div');
                    div.className = 'prompt-template-item'; div.dataset.promptName = prompt.name;
                    let labelText = prompt.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    if (prompt.name === 'classification_prompt_template') {
                        labelText = '分类提示词模板 (Classification Prompt Template)';
                    } // Add more specific translations if needed
                    div.innerHTML = `<label for="prompt-${prompt.name}">${labelText}:</label><textarea id="prompt-${prompt.name}" rows="6" style="width: 98%;">${prompt.content}</textarea>`;
                    promptTemplatesContainer.appendChild(div);
                });
            }
        } catch (error) { console.error("Failed to load AI config:", error); }
        finally { if (showLoader) hideGlobalLoader(); }
    }

    if (saveAIModelConfigButton) {
        saveAIModelConfigButton.addEventListener('click', async () => {
            const originalButtonText = saveAIModelConfigButton.textContent;
            saveAIModelConfigButton.disabled = true; saveAIModelConfigButton.textContent = '保存中... (Saving...)';
            
            const payload = { default_llm_service: defaultLlmServiceSelect.value, llm_services_update: {} };
            const serviceFieldsets = llmServicesConfigsContainer.querySelectorAll('.service-config-fieldset');
            serviceFieldsets.forEach(fieldset => { 
                const serviceName = fieldset.dataset.serviceName;
                const apiKeyInput = document.getElementById(`${serviceName}-api-key`);
                const modelNameInput = document.getElementById(`${serviceName}-model-name`);
                const temperatureInput = document.getElementById(`${serviceName}-temperature`);
                const maxTokensInput = document.getElementById(`${serviceName}-max-tokens`);
                const serviceUpdate = { model_params: {} }; let hasUpdate = false;
                if (apiKeyInput && apiKeyInput.value.trim() !== '') { serviceUpdate.api_key = apiKeyInput.value.trim(); hasUpdate = true; }
                if (modelNameInput && modelNameInput.value.trim() !== '') { serviceUpdate.model_params.model_name = modelNameInput.value.trim(); hasUpdate = true; }
                if (temperatureInput && temperatureInput.value.trim() !== '') { const temp = parseFloat(temperatureInput.value); if (!isNaN(temp)) { serviceUpdate.model_params.temperature = temp; hasUpdate = true;}}
                if (maxTokensInput && maxTokensInput.value.trim() !== '') { const tokens = parseInt(maxTokensInput.value, 10); if (!isNaN(tokens)) { serviceUpdate.model_params.max_tokens = tokens; hasUpdate = true;}}
                if (hasUpdate) { if (Object.keys(serviceUpdate.model_params).length === 0) delete serviceUpdate.model_params; payload.llm_services_update[serviceName] = serviceUpdate; }
            });
            if (Object.keys(payload.llm_services_update).length === 0) delete payload.llm_services_update;

            try {
                await fetchAPI('/api/v1/settings/ai_config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                showToast('AI模型配置已保存！(AI model configuration saved successfully!)', 'success');
                loadAIConfig(false); 
            } catch (error) { console.error("Failed to save AI model config:", error); }
            finally {
                saveAIModelConfigButton.disabled = false; saveAIModelConfigButton.textContent = originalButtonText;
            }
        });
    }

    if (savePromptsButton) {
        savePromptsButton.addEventListener('click', async () => {
            const originalButtonText = savePromptsButton.textContent;
            savePromptsButton.disabled = true; savePromptsButton.textContent = '保存中... (Saving...)';

            const payload = { prompt_templates_update: [] };
            const promptItems = promptTemplatesContainer.querySelectorAll('.prompt-template-item');
            promptItems.forEach(item => { 
                const promptName = item.dataset.promptName; const textarea = item.querySelector('textarea');
                if (promptName && textarea) payload.prompt_templates_update.push({ name: promptName, content: textarea.value });
            });
            if (payload.prompt_templates_update.length === 0) { 
                showToast('未找到可更新的提示词模板。(No prompt templates found to update.)', 'info'); 
                savePromptsButton.disabled = false; savePromptsButton.textContent = originalButtonText; 
                return; 
            }

            try {
                await fetchAPI('/api/v1/settings/ai_config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                showToast('提示词模板已保存！(Prompt templates saved successfully!)', 'success');
                loadAIConfig(false); 
            } catch (error) { console.error("Failed to save prompt templates:", error); }
            finally {
                savePromptsButton.disabled = false; savePromptsButton.textContent = originalButtonText;
            }
        });
    }

    function renderCategories(categoriesData) { 
        if (!categoriesListContainer) return; categoriesListContainer.innerHTML = '';
        if (Object.keys(categoriesData).length === 0) { categoriesListContainer.innerHTML = '<p>尚未定义分类。(No categories defined yet.)</p>'; return; }
        for (const [l1Name, l2List] of Object.entries(categoriesData)) {
            const l1ItemDiv = document.createElement('div'); l1ItemDiv.className = 'l1-category-item'; l1ItemDiv.dataset.l1Name = l1Name;
            l1ItemDiv.innerHTML = `<h4><span class="l1-name-display">${l1Name}</span><input type="text" class="edit-l1-name-input" value="${l1Name}" style="display:none; flex-grow:1; margin-left:5px; margin-right:5px;"><button class="edit-l1-btn">编辑 (Edit)</button><button class="save-l1-btn" style="display:none;">保存 (Save)</button><button class="cancel-edit-l1-btn" style="display:none;">取消 (Cancel)</button><button class="delete-l1-btn">删除 (Delete)</button><button class="add-l2-btn">添加L2 (Add L2)</button></h4><ul class="l2-category-list"></ul><div class="add-l2-form" style="display:none; margin-left: 20px; margin-top: 5px;"><input type="text" class="new-l2-category-name" placeholder="新L2类别名称 (New L2 Name)"><button class="save-new-l2-btn">保存L2 (Save L2)</button><button class="cancel-add-l2-btn">取消 (Cancel)</button></div>`;
            const ulL2List = l1ItemDiv.querySelector('.l2-category-list');
            if (l2List && l2List.length > 0) {
                l2List.forEach(l2Name => {
                    const li = document.createElement('li'); li.dataset.l2Name = l2Name;
                    li.innerHTML = `<span class="l2-name-display">${l2Name}</span><input type="text" class="edit-l2-name-input" value="${l2Name}" style="display:none; flex-grow:1; margin-left:5px; margin-right:5px;"><button class="edit-l2-btn">编辑 (Edit)</button><button class="save-l2-btn" style="display:none;">保存 (Save)</button><button class="cancel-edit-l2-btn" style="display:none;">取消 (Cancel)</button><button class="delete-l2-btn">删除 (Delete)</button>`;
                    ulL2List.appendChild(li);
                });
            } else { ulL2List.innerHTML = '<li>无二级分类。(No L2 categories defined.)</li>'; }
            categoriesListContainer.appendChild(l1ItemDiv);
        }
    }

    async function loadCategories(showLoader = true) { 
        if (showLoader) showGlobalLoader();
        try {
            const responseData = await fetchAPI('/api/v1/settings/categories', {}, !showLoader); 
            if (responseData) renderCategories(responseData.categories); 
        } catch (error) { console.error("Failed to load categories:", error); }
        finally { if (showLoader) hideGlobalLoader(); }
    }

    if (categoriesListContainer) {
        categoriesListContainer.addEventListener('click', async function(event) {
            const target = event.target;
            const l1ItemDiv = target.closest('.l1-category-item');
            const l1Name = l1ItemDiv?.dataset.l1Name;
            const liL2Item = target.closest('li[data-l2-name]');
            const l2Name = liL2Item?.dataset.l2Name;

            async function handleCategoryAction(button, actionPromise, successMessage) {
                if (!button) return;
                const originalText = button.textContent;
                button.disabled = true; button.textContent = '保存中... (Saving...)';
                try {
                    await actionPromise;
                    showToast(successMessage, 'success');
                    loadCategories(false); 
                } catch (error) { /* fetchAPI shows toast */ }
                finally {
                    button.disabled = false; button.textContent = originalText;
                }
            }

            if (target.classList.contains('edit-l1-btn')) { 
                l1ItemDiv.querySelector('.l1-name-display').style.display = 'none'; l1ItemDiv.querySelector('.edit-l1-name-input').style.display = 'inline-block'; target.style.display = 'none'; l1ItemDiv.querySelector('.save-l1-btn').style.display = 'inline-block'; l1ItemDiv.querySelector('.cancel-edit-l1-btn').style.display = 'inline-block';
            } else if (target.classList.contains('cancel-edit-l1-btn')) {  
                 l1ItemDiv.querySelector('.l1-name-display').style.display = 'inline-block'; l1ItemDiv.querySelector('.edit-l1-name-input').style.display = 'none'; l1ItemDiv.querySelector('.edit-l1-name-input').value = l1Name; target.style.display = 'none'; l1ItemDiv.querySelector('.save-l1-btn').style.display = 'none'; l1ItemDiv.querySelector('.edit-l1-btn').style.display = 'inline-block';
            } else if (target.classList.contains('save-l1-btn')) {
                const newL1Name = l1ItemDiv.querySelector('.edit-l1-name-input').value.trim();
                if (newL1Name && newL1Name !== l1Name) {
                    handleCategoryAction(target, fetchAPI(`/api/v1/settings/categories/l1/${encodeURIComponent(l1Name)}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ new_name: newL1Name }) }), `L1分类 '${l1Name}' 已更新为 '${newL1Name}'. (L1 '${l1Name}' updated to '${newL1Name}'.)`);
                } else if (newL1Name === l1Name) l1ItemDiv.querySelector('.cancel-edit-l1-btn').click();
                else showToast('新L1类别名称不能为空。(New L1 name cannot be empty.)', 'error');
            } else if (target.classList.contains('delete-l1-btn')) {
                if (confirm(`确定要删除L1类别 "${l1Name}" 及其所有L2子类别吗？(Delete L1 category "${l1Name}" and all its L2s?)`)) {
                    handleCategoryAction(target, fetchAPI(`/api/v1/settings/categories/l1/${encodeURIComponent(l1Name)}`, { method: 'DELETE' }), `L1分类 '${l1Name}' 已删除。(L1 category '${l1Name}' deleted.)`);
                }
            } else if (target.classList.contains('add-l2-btn')) { 
                l1ItemDiv.querySelector('.add-l2-form').style.display = 'block';
            } else if (target.classList.contains('cancel-add-l2-btn')) { 
                const addL2Form = target.closest('.add-l2-form'); addL2Form.style.display = 'none'; addL2Form.querySelector('.new-l2-category-name').value = '';
            } else if (target.classList.contains('save-new-l2-btn')) {
                const newL2NameInput = target.closest('.add-l2-form').querySelector('.new-l2-category-name');
                const newL2Name = newL2NameInput.value.trim();
                if (newL2Name && l1Name) {
                    handleCategoryAction(target, fetchAPI(`/api/v1/settings/categories/l1/${encodeURIComponent(l1Name)}/l2`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ name: newL2Name }) }), `L2分类 '${newL2Name}' 已添加到L1 '${l1Name}'. (L2 '${newL2Name}' added to L1 '${l1Name}'.)`);
                } else showToast('新L2类别名称不能为空。(New L2 name cannot be empty.)', 'error');
            } else if (target.classList.contains('edit-l2-btn') && liL2Item) { 
                liL2Item.querySelector('.l2-name-display').style.display = 'none'; liL2Item.querySelector('.edit-l2-name-input').style.display = 'inline-block'; target.style.display = 'none'; liL2Item.querySelector('.save-l2-btn').style.display = 'inline-block'; liL2Item.querySelector('.cancel-edit-l2-btn').style.display = 'inline-block';
            } else if (target.classList.contains('cancel-edit-l2-btn') && liL2Item) { 
                liL2Item.querySelector('.l2-name-display').style.display = 'inline-block'; liL2Item.querySelector('.edit-l2-name-input').style.display = 'none'; liL2Item.querySelector('.edit-l2-name-input').value = l2Name; target.style.display = 'none'; liL2Item.querySelector('.save-l2-btn').style.display = 'none'; liL2Item.querySelector('.edit-l2-btn').style.display = 'inline-block';
            } else if (target.classList.contains('save-l2-btn') && liL2Item && l1Name) {
                const newL2Name = liL2Item.querySelector('.edit-l2-name-input').value.trim();
                if (newL2Name && newL2Name !== l2Name) {
                    handleCategoryAction(target, fetchAPI(`/api/v1/settings/categories/l2/${encodeURIComponent(l1Name)}/${encodeURIComponent(l2Name)}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ new_name: newL2Name }) }), `L2分类 '${l2Name}' 已更新为 '${newL2Name}'. (L2 '${l2Name}' updated to '${newL2Name}'.)`);
                } else if (newL2Name === l2Name) liL2Item.querySelector('.cancel-edit-l2-btn').click();
                else showToast('新L2类别名称不能为空。(New L2 name cannot be empty.)', 'error');
            } else if (target.classList.contains('delete-l2-btn') && liL2Item && l1Name) {
                if (confirm(`确定要从L1 "${l1Name}" 删除L2类别 "${l2Name}" 吗？(Delete L2 category "${l2Name}" from L1 "${l1Name}"?)`)) {
                    handleCategoryAction(target, fetchAPI(`/api/v1/settings/categories/l2/${encodeURIComponent(l1Name)}/${encodeURIComponent(l2Name)}`, { method: 'DELETE' }), `L2分类 '${l2Name}' 已从L1 '${l1Name}' 删除。(L2 category '${l2Name}' deleted from L1 '${l1Name}'.)`);
                }
            }
        });
    }

    if (addL1CategoryButton) {
        addL1CategoryButton.addEventListener('click', async () => {
            const newL1Name = newL1CategoryNameInput.value.trim();
            if (!newL1Name) { showToast('新L1类别名称不能为空。(New L1 category name cannot be empty.)', 'error'); return; }

            const originalButtonText = addL1CategoryButton.textContent;
            addL1CategoryButton.disabled = true; addL1CategoryButton.textContent = '添加中... (Adding...)';
            try {
                await fetchAPI('/api/v1/settings/categories/l1', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ name: newL1Name }) });
                showToast(`L1分类 '${newL1Name}' 已添加。(L1 category '${newL1Name}' added.)`, 'success');
                newL1CategoryNameInput.value = ''; 
                loadCategories(false); 
            } catch (error) { /* fetchAPI shows toast */ }
            finally {
                addL1CategoryButton.disabled = false; addL1CategoryButton.textContent = originalButtonText;
            }
        });
    }

    async function initialLoad() { 
        showGlobalLoader(); 
        try {
            await Promise.all([loadAIConfig(false), loadCategories(false)]);
            showToast("设置页面已加载。(Settings page loaded successfully.)", "success");
        } catch (error) {
            showToast("加载设置页面组件时出错。(Error loading some settings page components.)", "error");
            console.error("Error during initial settings page load:", error);
        } finally {
            hideGlobalLoader(); 
        }
    }
    initialLoad();
});
