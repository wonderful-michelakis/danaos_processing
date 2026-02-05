/**
 * Correction Modal
 * Handles entity correction UI, API interactions, and state management
 */

class CorrectionModal {
    constructor(comparator) {
        this.comparator = comparator;  // Reference to DocumentComparator
        this.currentEntityId = null;
        this.currentEntityType = null;
        this.currentEntityPage = null;
        this.originalContent = null;
        this.currentTab = 'manual';  // 'manual' or 'ai'

        // DOM elements
        this.modal = document.getElementById('correction-modal');
        this.overlay = this.modal.querySelector('.modal-overlay');
        this.closeBtn = this.modal.querySelector('.close-btn');
        this.cancelBtn = document.getElementById('cancel-btn');
        this.saveBtn = document.getElementById('save-correction-btn');
        this.generateBtn = document.getElementById('generate-correction-btn');

        // Tab elements
        this.manualTab = document.getElementById('manual-tab');
        this.aiTab = document.getElementById('ai-tab');
        this.tabBtns = document.querySelectorAll('.tab-btn');

        // Content elements
        this.modalEntityId = document.getElementById('modal-entity-id');
        this.modalEntityType = document.getElementById('modal-entity-type');
        this.modalEntityPage = document.getElementById('modal-entity-page');
        this.originalContentPre = document.getElementById('original-content');
        this.manualEdit = document.getElementById('manual-edit');
        this.manualReason = document.getElementById('manual-reason');
        this.aiPrompt = document.getElementById('ai-prompt');
        this.aiResult = document.getElementById('ai-result');
        this.aiCorrectedContent = document.getElementById('ai-corrected-content');
        this.aiEdit = document.getElementById('ai-edit');

        // Loading overlay
        this.loadingOverlay = document.getElementById('modal-loading');

        this.setupEventListeners();
    }

    async open(entityId) {
        try {
            // Fetch entity content from API
            const response = await fetch(`/api/entity/${entityId}`);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to fetch entity');
            }

            const entityData = await response.json();

            // Store entity data
            this.currentEntityId = entityData.entity_id;
            this.currentEntityType = entityData.type;
            this.currentEntityPage = entityData.page;
            this.originalContent = entityData.content;

            // Populate modal fields
            this.modalEntityId.textContent = entityData.entity_id;
            this.modalEntityType.textContent = entityData.type;
            this.modalEntityPage.textContent = entityData.page;
            this.originalContentPre.textContent = entityData.content;
            this.manualEdit.value = entityData.content;  // Pre-fill with original content
            this.manualReason.value = '';
            this.aiPrompt.value = '';

            // Reset AI tab
            this.aiResult.style.display = 'none';
            this.aiCorrectedContent.textContent = '';
            this.aiEdit.value = '';

            // Reset to manual tab
            this.switchTab('manual');

            // Show modal
            this.modal.style.display = 'block';

        } catch (error) {
            console.error('Error opening modal:', error);
            this.showError(`Failed to load entity: ${error.message}`);
        }
    }

    close() {
        // Hide modal
        this.modal.style.display = 'none';

        // Reset form
        this.currentEntityId = null;
        this.currentEntityType = null;
        this.currentEntityPage = null;
        this.originalContent = null;
        this.manualEdit.value = '';
        this.manualReason.value = '';
        this.aiPrompt.value = '';
        this.aiResult.style.display = 'none';
    }

    switchTab(tabName) {
        this.currentTab = tabName;

        // Update tab buttons
        this.tabBtns.forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update tab content
        if (tabName === 'manual') {
            this.manualTab.style.display = 'block';
            this.aiTab.style.display = 'none';
        } else if (tabName === 'ai') {
            this.manualTab.style.display = 'none';
            this.aiTab.style.display = 'block';
        }
    }

    async generateAICorrection() {
        try {
            const userPrompt = this.aiPrompt.value.trim();

            if (!userPrompt) {
                this.showError('Please describe the issue');
                return;
            }

            // Show loading
            this.showLoading();

            // Call AI correction API
            const response = await fetch('/api/correct-with-ai', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    entity_id: this.currentEntityId,
                    user_prompt: userPrompt
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'AI correction failed');
            }

            const data = await response.json();

            // Populate AI result
            this.aiCorrectedContent.textContent = data.corrected_content;
            this.aiEdit.value = data.corrected_content;

            // Show AI result section
            this.aiResult.style.display = 'block';

            // Hide loading
            this.hideLoading();

        } catch (error) {
            console.error('AI correction error:', error);
            this.hideLoading();
            this.showError(`AI correction failed: ${error.message}`);
        }
    }

    async saveCorrection() {
        try {
            let correctedContent, correctionType, reason, userPrompt = null;

            // Get data based on current tab
            if (this.currentTab === 'manual') {
                correctedContent = this.manualEdit.value.trim();
                reason = this.manualReason.value.trim();
                correctionType = 'manual';

                if (!correctedContent || !reason) {
                    this.showError('Please provide corrected content and reason');
                    return;
                }
            } else if (this.currentTab === 'ai') {
                correctedContent = this.aiEdit.value.trim();
                reason = 'AI-assisted correction';
                correctionType = 'ai';
                userPrompt = this.aiPrompt.value.trim();

                if (!correctedContent) {
                    this.showError('Please generate AI correction first');
                    return;
                }
            }

            // Check if content actually changed
            if (correctedContent === this.originalContent) {
                this.showError('Content unchanged - no correction needed');
                return;
            }

            // Show loading
            this.showLoading();

            // Save correction via API
            const response = await fetch('/api/save-correction', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    entity_id: this.currentEntityId,
                    corrected_content: correctedContent,
                    correction_type: correctionType,
                    reason: reason,
                    user_prompt: userPrompt
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save correction');
            }

            const data = await response.json();

            // Store entity ID before closing (close() resets it to null)
            const savedEntityId = this.currentEntityId;

            // Hide loading
            this.hideLoading();

            // Close modal
            this.close();

            // Reload HTML content
            await this.comparator.reloadHTMLContent();

            // Highlight corrected entity
            this.comparator.highlightCorrectedEntity(savedEntityId);

            // Show success message
            this.comparator.showSuccess(`✓ Correction saved for ${savedEntityId}`);

        } catch (error) {
            console.error('Save correction error:', error);
            this.hideLoading();
            this.showError(`Save failed: ${error.message}`);
        }
    }

    setupEventListeners() {
        // Close button
        this.closeBtn.addEventListener('click', () => {
            this.close();
        });

        // Cancel button
        this.cancelBtn.addEventListener('click', () => {
            this.close();
        });

        // Overlay click to close
        this.overlay.addEventListener('click', () => {
            this.close();
        });

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.style.display === 'block') {
                this.close();
            }
        });

        // Tab switching
        this.tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchTab(btn.dataset.tab);
            });
        });

        // Generate AI correction button
        this.generateBtn.addEventListener('click', () => {
            this.generateAICorrection();
        });

        // Save correction button
        this.saveBtn.addEventListener('click', () => {
            this.saveCorrection();
        });
    }

    showLoading() {
        this.loadingOverlay.style.display = 'flex';
    }

    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }

    showError(message) {
        // Display error using comparator's error display
        if (this.comparator && this.comparator.showError) {
            this.comparator.showError(message);
        } else {
            alert(message);
        }
    }
}
