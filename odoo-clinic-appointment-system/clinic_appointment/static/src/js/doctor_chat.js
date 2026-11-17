(function () {
    'use strict';

    var currentSessionUuid = null;
    var pollingInterval    = null;
    var lastMessageId      = 0;
    var doctorIsOnline     = false;

    function esc(text) {
        var d = document.createElement('div');
        d.textContent = String(text || '');
        return d.innerHTML;
    }

    function nowStr() {
        return new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    }

    function post(url, payload) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},
            body: JSON.stringify(payload || {})
        }).then(function(r) { return r.json(); });
    }

    // ── Online status ───────────────────────────────────────────────
    function fetchStatus() {
        post('/clinic/doctor/online/status')
        .then(function(data) {
            applyStatus(((data||{}).result||{}).is_online === true);
        })
        .catch(function(e) { console.error('[DC] status:', e); });
    }

    function applyStatus(isOnline) {
        doctorIsOnline = isOnline;
        var sp  = document.getElementById('doctorStatus');
        var on  = document.getElementById('goOnlineBtn');
        var off = document.getElementById('goOfflineBtn');
        if (isOnline) {
            if (sp)  sp.innerHTML = '<span style="color:#28a745;">🟢 Online</span>';
            if (on)  on.style.display  = 'none';
            if (off) off.style.display = 'inline-block';
        } else {
            if (sp)  sp.innerHTML = '<span style="color:#dc3545;">🔴 Offline</span>';
            if (on)  on.style.display  = 'inline-block';
            if (off) off.style.display = 'none';
        }
    }

    function setOnline(flag) {
        post('/clinic/doctor/online/toggle', {is_online: flag})
        .then(function(data) { applyStatus(((data||{}).result||{}).is_online === true); })
        .catch(function(e) { console.error('[DC] toggle:', e); });
    }

    // ── Accept chat — then auto-open the chat panel ─────────────────
    window.acceptChat = function(sessionId) {
        var sid = parseInt(sessionId, 10);
        if (!sid || isNaN(sid)) {
            alert('Invalid session. Please refresh the page.');
            return;
        }
        if (!doctorIsOnline) {
            alert('⚠️ You are Offline.\nPlease click "Go Online" first.');
            return;
        }

        post('/clinic/doctor/chat/accept', {session_id: sid})
        .then(function(data) {
            var res = (data||{}).result || {};
            if (res.status === 'accepted') {
                // Reload page with the session UUID as a query param
                // so we auto-open the chat panel after reload
                window.location.href =
                    '/clinic/doctor/chat/list?open_session=' + encodeURIComponent(res.session_id);
            } else {
                alert('Could not accept: ' + (res.error || 'Unknown error'));
            }
        })
        .catch(function(e) {
            console.error('[DC] accept:', e);
            alert('Network error accepting chat.');
        });
    };

    // ── Refresh waiting list every 10s ──────────────────────────────
    function refreshWaiting() {
        post('/clinic/doctor/chat/waiting')
        .then(function(data) {
            var sessions  = ((data||{}).result||{}).sessions || [];
            var container = document.getElementById('waiting-list-container');
            if (!container) return;

            if (!sessions.length) {
                container.innerHTML =
                    '<div class="alert alert-secondary">No patients waiting.</div>';
                return;
            }
            container.innerHTML = sessions.map(function(s) {
                var sid = parseInt(s.id, 10);
                return (
                    '<div class="alert alert-warning waiting-row d-flex' +
                    ' justify-content-between align-items-center mb-2">' +
                    '<div><strong>' + esc(s.patient_name) + '</strong>' +
                    '<span class="text-muted ms-2">—</span>' +
                    '<span class="ms-1">' + esc(s.specialization) + '</span></div>' +
                    '<button class="btn btn-success btn-sm"' +
                    ' onclick="window.acceptChat(' + sid + ')"> Accept Chat</button>' +
                    '</div>'
                );
            }).join('');
        })
        .catch(function(e) { console.error('[DC] waiting refresh:', e); });
    }

    // ── Open chat panel ─────────────────────────────────────────────
    window.openDoctorChat = function(sessionId, sessionUuid, patientName) {
        currentSessionUuid = sessionUuid;
        lastMessageId      = 0;

        var panel = document.getElementById('doctor-active-chat');
        if (!panel) {
            var cb = document.querySelector('.card-body');
            if (!cb) { console.error('[DC] .card-body not found'); return; }
            cb.insertAdjacentHTML('beforeend', buildPanel(patientName));
            panel = document.getElementById('doctor-active-chat');
            wirePanelButtons();
        } else {
            panel.style.display = 'block';
            var ns = document.getElementById('dc-patient-name');
            if (ns) ns.textContent = '💬 Chat with ' + (patientName || 'Patient');
            var mb = document.getElementById('dc-messages');
            if (mb) mb.innerHTML = placeHolder();
        }

        // Scroll the panel into view
        setTimeout(function() {
            if (panel) panel.scrollIntoView({behavior:'smooth', block:'start'});
        }, 100);

        if (pollingInterval) clearInterval(pollingInterval);
        pollingInterval = setInterval(pollChat, 3000);
        pollChat(); // immediate first fetch
    };

    function placeHolder() {
        return '<div id="dc-placeholder" style="text-align:center;color:#aaa;font-size:13px;padding:20px;">Loading messages…</div>';
    }

    function buildPanel(patientName) {
        return (
            '<div id="doctor-active-chat" style="margin-top:24px;border:1px solid #dee2e6;' +
            'border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.08);">' +

            '<div style="background:linear-gradient(90deg,#00a09d,#017a77);color:white;' +
            'padding:12px 16px;display:flex;justify-content:space-between;align-items:center;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
            '<div style="width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,0.2);' +
            'display:flex;align-items:center;justify-content:center;font-size:18px;">👤</div>' +
            '<div>' +
            '<div id="dc-patient-name" style="font-weight:700;font-size:15px;">💬 Chat with ' +
            esc(patientName || 'Patient') + '</div>' +
            '<div style="font-size:12px;opacity:0.8;">● Active session</div>' +
            '</div></div>' +
            '<div>' +
            '<button id="dc-end-btn" style="background:#dc3545;border:none;color:white;' +
            'padding:6px 14px;border-radius:6px;cursor:pointer;margin-right:8px;font-size:13px;">End</button>' +
            '<button id="dc-close-btn" style="background:rgba(255,255,255,0.2);border:none;' +
            'color:white;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:13px;">✕</button>' +
            '</div></div>' +

            '<div id="dc-messages" style="height:340px;overflow-y:auto;padding:14px;background:#f8f9fa;">' +
            placeHolder() +
            '</div>' +

            '<div style="display:flex;gap:8px;padding:12px 14px;border-top:1px solid #dee2e6;background:white;">' +
            '<input type="text" id="dc-input" placeholder="Type your reply…"' +
            ' style="flex:1;padding:10px 14px;border:1.5px solid #e5e7eb;border-radius:20px;' +
            'font-size:14px;outline:none;font-family:inherit;"/>' +
            '<button id="dc-send-btn" style="padding:10px 22px;background:#00a09d;color:white;' +
            'border:none;border-radius:20px;cursor:pointer;font-size:14px;font-weight:600;">' +
            'Send</button>' +
            '</div></div>'
        );
    }

    // ── Poll patient messages ────────────────────────────────────────
    function pollChat() {
        if (!currentSessionUuid) return;
        post('/clinic/doctor/chat/poll', {
            session_id: currentSessionUuid,
            last_id:    lastMessageId
        })
        .then(function(data) {
            var msgs = ((data||{}).result||{}).messages || [];
            if (!msgs.length) return;

            var box = document.getElementById('dc-messages');
            if (!box) return;

            var ph = document.getElementById('dc-placeholder');
            if (ph) ph.remove();

            msgs.forEach(function(m) {
                var isSys = m.sender_type === 'system';
                var bg    = isSys ? '#fff3cd' : '#e9ecef';
                var fg    = isSys ? '#856404' : '#212529';
                var lbl   = isSys ? '🔔 System' : ('👤 ' + esc(m.sender_name || 'Patient'));

                var div = document.createElement('div');
                div.style.marginBottom = '10px';
                div.innerHTML =
                    '<div style="display:inline-block;max-width:80%;padding:10px 14px;' +
                    'border-radius:18px;background:' + bg + ';color:' + fg + ';' +
                    'box-shadow:0 1px 3px rgba(0,0,0,0.06);">' +
                    '<div style="font-size:11px;font-weight:700;opacity:0.65;margin-bottom:3px;">' +
                    lbl + '</div>' +
                    esc(m.message) +
                    '<div style="font-size:10px;margin-top:4px;opacity:0.5;text-align:right;">' +
                    esc(m.timestamp || '') + '</div></div>';

                box.appendChild(div);
                lastMessageId = m.id;
            });
            box.scrollTop = box.scrollHeight;
        })
        .catch(function(e) { console.error('[DC] poll:', e); });
    }

    // ── Chat panel button events ────────────────────────────────────
    function wirePanelButtons() {
        var sendBtn  = document.getElementById('dc-send-btn');
        var input    = document.getElementById('dc-input');
        var closeBtn = document.getElementById('dc-close-btn');
        var endBtn   = document.getElementById('dc-end-btn');

        function doSend() {
            var msg = input ? input.value.trim() : '';
            if (!msg || !currentSessionUuid) return;
            if (input) input.value = '';

            // Optimistic bubble (doctor's own message)
            var box = document.getElementById('dc-messages');
            if (box) {
                var div = document.createElement('div');
                div.style.cssText = 'margin-bottom:10px;text-align:right;';
                div.innerHTML =
                    '<div style="display:inline-block;max-width:80%;padding:10px 14px;' +
                    'border-radius:18px;background:#00a09d;color:white;' +
                    'box-shadow:0 1px 3px rgba(0,0,0,0.1);">' +
                    '<div style="font-size:11px;font-weight:700;opacity:0.8;margin-bottom:3px;">You</div>' +
                    esc(msg) +
                    '<div style="font-size:10px;margin-top:4px;opacity:0.6;text-align:right;">' +
                    nowStr() + '</div></div>';
                box.appendChild(div);
                box.scrollTop = box.scrollHeight;
            }

            post('/clinic/doctor/chat/send', {session_id: currentSessionUuid, message: msg})
            .catch(function(e) { console.error('[DC] send:', e); });
        }

        if (sendBtn) sendBtn.onclick = doSend;
        if (input) {
            input.onkeypress = function(e) { if (e.key === 'Enter') doSend(); };
            // Style focus
            input.onfocus = function() { this.style.borderColor = '#00a09d'; };
            input.onblur  = function() { this.style.borderColor = '#e5e7eb'; };
        }

        if (closeBtn) closeBtn.onclick = function() {
            var p = document.getElementById('doctor-active-chat');
            if (p) p.style.display = 'none';
            if (pollingInterval) clearInterval(pollingInterval);
            currentSessionUuid = null;
        };

        if (endBtn) endBtn.onclick = function() {
            if (!currentSessionUuid) return;
            if (!confirm('End this consultation with the patient?')) return;
            post('/clinic/doctor/chat/end', {session_id: currentSessionUuid})
            .then(function() {
                if (pollingInterval) clearInterval(pollingInterval);
                currentSessionUuid = null;
                location.href = '/clinic/doctor/chat/list';
            })
            .catch(function(e) { console.error('[DC] end:', e); });
        };
    }

    // ── Check URL for auto-open after accept ────────────────────────
    function checkAutoOpen() {
        var params     = new URLSearchParams(window.location.search);
        var openSessId = params.get('open_session');
        if (!openSessId) return;

        // Clean URL without reloading
        var cleanUrl = window.location.pathname;
        window.history.replaceState({}, '', cleanUrl);

        // Find the active session row that matches this UUID and open it
        // We poll the active sessions via the page DOM
        var openBtns = document.querySelectorAll('.open-chat-btn');
        for (var i = 0; i < openBtns.length; i++) {
            if (openBtns[i].getAttribute('data-uuid') === openSessId) {
                openBtns[i].click();
                return;
            }
        }

        // Fallback: fetch session info and open directly
        post('/clinic/doctor/chat/session-info', {session_uuid: openSessId})
        .then(function(data) {
            var res = (data||{}).result || {};
            if (res.session_id) {
                window.openDoctorChat(res.db_id, res.session_id, res.patient_name);
            }
        })
        .catch(function(e) { console.error('[DC] auto-open:', e); });
    }

    // ── Init ────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function() {

        var onBtn  = document.getElementById('goOnlineBtn');
        var offBtn = document.getElementById('goOfflineBtn');
        if (onBtn)  onBtn.onclick  = function() { setOnline(true);  };
        if (offBtn) offBtn.onclick = function() { setOnline(false); };

        // Wire "Open Chat" buttons on page load
        document.querySelectorAll('.open-chat-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                window.openDoctorChat(
                    this.getAttribute('data-id'),
                    this.getAttribute('data-uuid'),
                    this.getAttribute('data-patient')
                );
            });
        });

        fetchStatus();
        setInterval(refreshWaiting, 10000);

        // Auto-open chat if redirected from acceptChat()
        checkAutoOpen();
    });

})();