(function () {
    'use strict';

    var currentSessionUuid = null;
    var lastMessageId      = 0;
    var pollTimer          = null;
    var hasUnread          = false;   // for tab title flash

    var patientName            = '';
    var selectedSpecialization = '';

    // ── JSONRPC helper ───────────────────────────────────────────────
    function rpcPost(url, params) {
        return fetch(url, {
            method:  'POST',
            headers: {
                'Content-Type':     'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method:  'call',
                id:      null,
                params:  params || {},
            }),
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.error) {
                var msg = (data.error.data && data.error.data.message)
                    ? data.error.data.message
                    : JSON.stringify(data.error);
                throw new Error(msg);
            }
            return data.result || {};
        });
    }

    // ── Utility ──────────────────────────────────────────────────────
    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = String(text || '');
        return div.innerHTML;
    }

    function nowTime() {
        return new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    }

    // ── FIX 1: Inline error display instead of alert() ───────────────
    function showFormError(message) {
        // Remove any existing error
        var existing = document.getElementById('chat_form_error');
        if (existing) existing.remove();

        var errDiv = document.createElement('div');
        errDiv.id = 'chat_form_error';
        errDiv.style.cssText = [
            'color:#dc3545',
            'background:#fdecea',
            'border:1px solid #f5c6cb',
            'padding:10px 14px',
            'border-radius:8px',
            'margin-top:10px',
            'font-size:14px',
            'line-height:1.5',
        ].join(';');
        errDiv.textContent = '⚠️ ' + message;

        var startBtn = document.getElementById('start_btn');
        if (startBtn && startBtn.parentNode) {
            startBtn.parentNode.insertBefore(errDiv, startBtn);
        }

        // Auto-dismiss after 5 seconds
        setTimeout(function () {
            if (errDiv.parentNode) errDiv.remove();
        }, 5000);
    }

    function clearFormError() {
        var existing = document.getElementById('chat_form_error');
        if (existing) existing.remove();
    }

    // ── Chat bubble renderer ─────────────────────────────────────────
    function addMessage(senderType, senderName, message) {
        var container = document.getElementById('chat_messages');
        if (!container) return;

        var isPatient = (senderType === 'patient');
        var isDoctor  = (senderType === 'doctor');

        var bubbleStyle, labelHtml, alignStyle;

        if (isPatient) {
            bubbleStyle = 'background:#00a09d; color:#fff;';
            labelHtml   = '👤 <strong>You</strong>';
            alignStyle  = 'text-align:right;';
        } else if (isDoctor) {
            bubbleStyle = 'background:#e9ecef; color:#212529; border:1px solid #ced4da;';
            labelHtml   = '👨‍⚕️ <strong>' + escapeHtml(senderName || 'Doctor') + '</strong>';
            alignStyle  = 'text-align:left;';
        } else {
            // system / AI
            bubbleStyle = 'background:#fff8e1; color:#555; border:1px solid #ffe082;';
            labelHtml   = '🔔 <strong>System</strong>';
            alignStyle  = 'text-align:left;';
        }

        var wrapper = document.createElement('div');
        wrapper.style.cssText = 'margin-bottom:12px; ' + alignStyle;
        wrapper.innerHTML =
            '<div style="display:inline-block; max-width:80%; padding:10px 14px;' +
            ' border-radius:18px; ' + bubbleStyle + '">' +
            labelHtml + '<br/>' +
            escapeHtml(message) +
            '<div style="font-size:10px; margin-top:4px; opacity:0.6;">' +
            nowTime() + '</div>' +
            '</div>';

        container.appendChild(wrapper);
        container.scrollTop = container.scrollHeight;
    }

    // ── Doctor status banner ─────────────────────────────────────────
    function setDoctorStatus(assigned, doctorName) {
        var el = document.getElementById('doctor_status');
        if (!el) return;

        if (assigned) {
            el.innerHTML        = '🟢 Dr. ' + escapeHtml(doctorName || 'Doctor') + ' has joined your consultation';
            el.style.color      = '#155724';
            el.style.background = '#d4edda';
            el.style.border     = '1px solid #c3e6cb';
            el.style.borderRadius = '8px';
            el.style.padding    = '8px';
        } else {
            el.innerHTML        = '⏳ Waiting for a doctor to accept your chat…';
            el.style.color      = '#856404';
            el.style.background = '#fff3cd';
            el.style.border     = '1px solid #ffc107';
            el.style.borderRadius = '8px';
            el.style.padding    = '8px';
        }
    }

    // ── FIX 5: Browser tab notification ─────────────────────────────
    var originalTitle = document.title;
    var titleTimer    = null;

    function flashTabTitle(message) {
        if (titleTimer) clearInterval(titleTimer);
        var toggle = false;
        titleTimer = setInterval(function () {
            document.title = toggle ? originalTitle : ('🔔 ' + message);
            toggle = !toggle;
        }, 1200);

        // Stop flashing when user focuses the tab
        window.addEventListener('focus', function stopFlash() {
            clearInterval(titleTimer);
            titleTimer = null;
            document.title = originalTitle;
            window.removeEventListener('focus', stopFlash);
        });
    }

    // ── Polling ──────────────────────────────────────────────────────
    function startPolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollMessages();  // immediate first fetch
        pollTimer = setInterval(pollMessages, 3000);
    }

    function pollMessages() {
        if (!currentSessionUuid) return;

        rpcPost('/clinic/patient/chat/poll', {
            session_id: currentSessionUuid,
            last_id:    lastMessageId,
        })
        .then(function (result) {
            var msgs = result.messages || [];

            msgs.forEach(function (m) {
                addMessage(m.sender, m.sender_name, m.message);
                if (m.id > lastMessageId) lastMessageId = m.id;
            });

            // FIX 5: Flash tab when doctor/system message arrives
            if (msgs.length > 0 && !document.hasFocus()) {
                flashTabTitle('Doctor replied');
            }

            // Update doctor status banner as soon as doctor is assigned
            if (result.doctor_assigned) {
                setDoctorStatus(true, result.doctor_name);
            }

            if (result.status === 'ended' || result.status === 'closed') {
                clearInterval(pollTimer);
                pollTimer = null;
                addMessage('system', 'System', '🏁 The consultation has ended. Thank you!');
                disableInput();
            }
        })
        .catch(function (err) {
            console.error('[PatientChat] Poll error:', err);
        });
    }

    function disableInput() {
        var btn   = document.getElementById('send_btn');
        var input = document.getElementById('message_input');
        if (btn)   { btn.disabled  = true;  btn.style.opacity  = '0.5'; }
        if (input) { input.disabled = true; input.placeholder  = 'Consultation ended.'; }
    }

    // ── Step 1 → Start Chat ──────────────────────────────────────────
    function startChat() {
        var nameEl   = document.getElementById('patient_name');
        var phoneEl  = document.getElementById('patient_phone');
        var specEl   = document.getElementById('specialization');
        var slotEl   = document.getElementById('preferred_slot');
        var startBtn = document.getElementById('start_btn');

        patientName            = nameEl  ? nameEl.value.trim()  : '';
        var patientPhone       = phoneEl ? phoneEl.value.trim() : '';
        selectedSpecialization = specEl  ? specEl.value.trim()  : '';
        var preferredSlot      = slotEl  ? slotEl.value.trim()  : '';

        clearFormError();

        // FIX 1: Inline validation instead of alert()
        if (!patientName || !patientPhone) {
            showFormError('Please enter your full name and phone number.');
            return;
        }
        if (!selectedSpecialization) {
            showFormError('Please select a specialization.');
            return;
        }

        // FIX 3: Spinner feedback on button
        if (startBtn) {
            startBtn.disabled      = true;
            startBtn.textContent   = '⏳ Connecting…';
            startBtn.style.opacity = '0.7';
        }

        rpcPost('/clinic/patient/chat/start', {
            patient_name:   patientName,
            patient_phone:  patientPhone,
            specialization: selectedSpecialization,
            preferred_slot: preferredSlot,
        })
        .then(function (result) {
            if (result.error) {
                // FIX 1: Show error inline, reset button
                showFormError(result.error);
                if (startBtn) {
                    startBtn.disabled      = false;
                    startBtn.textContent   = 'Start Chat';
                    startBtn.style.opacity = '1';
                }
                return;
            }

            currentSessionUuid = result.session_id;

            // Switch from Step 1 to Step 2
            var step1 = document.getElementById('step1');
            var step2 = document.getElementById('step2');
            if (step1) step1.style.display = 'none';
            if (step2) step2.style.display = 'block';

            // FIX 2: Show server greeting if present
            if (result.greeting) {
                addMessage('system', 'System', result.greeting);
            } else {
                // Guaranteed fallback — screen is never blank
                addMessage('system', 'System',
                    ' Chat started! Please describe your symptoms. ' +
                    'A doctor will accept your consultation shortly.'
                );
            }

            // FIX 4: Set doctor status banner immediately
            if (result.doctor_assigned) {
                setDoctorStatus(true, result.doctor_name);
            } else {
                setDoctorStatus(false, null);
            }

            // Begin polling for doctor messages
            startPolling();
        })
        .catch(function (err) {
            console.error('[PatientChat] Start error:', err);
            // FIX 1: Show network error inline
            showFormError('Network error — please try again. Detail: ' + err.message);
            if (startBtn) {
                startBtn.disabled      = false;
                startBtn.textContent   = 'Start Chat';
                startBtn.style.opacity = '1';
            }
        });
    }

    // ── Step 2 → Send a patient message ─────────────────────────────
    function sendMessage() {
        var input = document.getElementById('message_input');
        var msg   = input ? input.value.trim() : '';
        if (!msg || !currentSessionUuid) return;

        addMessage('patient', patientName, msg);  // optimistic render
        if (input) input.value = '';

        rpcPost('/clinic/patient/chat/send', {
            session_id:   currentSessionUuid,
            message:      msg,
            patient_name: patientName,
        })
        .then(function (result) {
            if (result.error) {
                addMessage('system', 'System', '⚠️ ' + result.error);
                return;
            }
            if (result.doctor_assigned) {
                setDoctorStatus(true, result.doctor_name);
            }
            if (result.status === 'ended' || result.status === 'closed') {
                clearInterval(pollTimer);
                pollTimer = null;
                addMessage('system', 'System', '🏁 The consultation has ended.');
                disableInput();
            }
        })
        .catch(function (err) {
            console.error('[PatientChat] Send error:', err);
            addMessage('system', 'System', '⚠️ Network error. Please try again.');
        });
    }

    // ── Wire DOM events ──────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        var startBtn = document.getElementById('start_btn');
        if (startBtn) startBtn.addEventListener('click', startChat);

        var sendBtn = document.getElementById('send_btn');
        if (sendBtn) sendBtn.addEventListener('click', sendMessage);

        var input = document.getElementById('message_input');
        if (input) {
            input.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') sendMessage();
            });
        }
    });

})();