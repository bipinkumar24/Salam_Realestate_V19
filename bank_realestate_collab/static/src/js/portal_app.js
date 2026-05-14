/**
 * BRE Customer Application Portal
 * Written for Odoo 15 / OWL 1 syntax.
 * Data is injected server-side into data-* attributes — no AJAX needed.
 */
(function () {
    'use strict';

    /* ── Status config ──────────────────────────────────────── */
    var STATUS = {
        not_submitted: { label: 'Not Submitted', cls: 's-not_submitted' },
        pending:       { label: 'Pending Review', cls: 's-pending'       },
        under_review:  { label: 'Under Review',  cls: 's-under_review'  },
        approved:      { label: 'Approved',       cls: 's-approved'      },
        rejected:      { label: 'Rejected',       cls: 's-rejected'      },
        on_hold:       { label: 'On Hold',        cls: 's-on_hold'       },
    };

    function getStatus(key) {
        return STATUS[key] || { label: key || '—', cls: 's-not_submitted' };
    }

    function money(n, sym) {
        if (!n) return '—';
        return (sym || '') + ' ' + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 });
    }

    function pin(x) { return x || '—'; }

    function h(tag, attrs, children) {
        var el = document.createElement(tag);
        if (attrs) {
            Object.keys(attrs).forEach(function(k) {
                if (k === 'className') el.className = attrs[k];
                else if (k === 'href')    el.href = attrs[k];
                else if (k === 'style')   el.style.cssText = attrs[k];
                else if (k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
                else el.setAttribute(k, attrs[k]);
            });
        }
        if (children) {
            if (typeof children === 'string') {
                el.textContent = children;
            } else if (Array.isArray(children)) {
                children.forEach(function(c) {
                    if (!c) return;
                    if (typeof c === 'string') el.appendChild(document.createTextNode(c));
                    else el.appendChild(c);
                });
            } else {
                el.appendChild(children);
            }
        }
        return el;
    }

    /* ══════════════════════════════════════════════════════════
       LIST PAGE
    ══════════════════════════════════════════════════════════ */
    function renderListPage(apps, container) {
        container.innerHTML = '';

        /* Stats */
        function count(s) { return apps.filter(function(a){ return a.bank_status === s; }).length; }
        var statsDiv = h('div', { className: 'bre-stats' }, [
            makeStatCard(apps.length, 'Total', ''),
            makeStatCard(count('approved'), 'Approved', 'green'),
            makeStatCard(count('pending') + count('under_review'), 'In Progress', 'amber'),
            makeStatCard(count('rejected'), 'Rejected', 'red'),
            makeStatCard(count('on_hold'), 'On Hold', 'teal'),
        ]);

        function makeStatCard(n, lbl, mod) {
            return h('div', { className: 'bre-stat' + (mod ? ' ' + mod : '') }, [
                h('div', { className: 'bre-stat-n' }, String(n)),
                h('div', { className: 'bre-stat-lbl' }, lbl),
            ]);
        }

        /* Toolbar */
        var searchInput = h('input', {
            className: 'bre-search', type: 'text',
            placeholder: 'Search by reference, property, city…',
        });

        var activeFilter = 'all';
        var filterBtns = {};

        function makeChip(label, key) {
            var btn = h('button', { className: 'bre-chip' + (key === 'all' ? ' active' : '') }, label);
            btn.addEventListener('click', function() {
                activeFilter = key;
                Object.keys(filterBtns).forEach(function(k) {
                    filterBtns[k].className = 'bre-chip' + (k === key ? ' active' : '');
                });
                renderCards();
            });
            filterBtns[key] = btn;
            return btn;
        }

        var toolbar = h('div', { className: 'bre-toolbar' }, [
            searchInput,
            makeChip('All', 'all'),
            makeChip('Approved', 'approved'),
            makeChip('Pending', 'pending'),
            makeChip('Under Review', 'under_review'),
            makeChip('Rejected', 'rejected'),
        ]);

        searchInput.addEventListener('input', renderCards);

        /* Card grid */
        var grid = h('div', { className: 'bre-grid' });

        function renderCards() {
            var q = searchInput.value.toLowerCase().trim();
            var filtered = apps.filter(function(a) {
                if (activeFilter !== 'all' && a.bank_status !== activeFilter) return false;
                if (!q) return true;
                return (a.name || '').toLowerCase().includes(q) ||
                       (a.property_name || '').toLowerCase().includes(q) ||
                       (a.property_city || '').toLowerCase().includes(q) ||
                       (a.stage || '').toLowerCase().includes(q);
            });
            grid.innerHTML = '';
            if (!filtered.length) {
                grid.appendChild(h('div', { className: 'bre-empty', style: 'grid-column:1/-1' }, [
                    h('div', { className: 'bre-empty-icon', style: 'font-size:40px' }, '📂'),
                    h('h3', {}, 'No applications found'),
                    h('p', {}, 'Try adjusting your search or filter.'),
                ]));
                return;
            }
            filtered.forEach(function(app) { grid.appendChild(makeCard(app)); });
        }

        function makeCard(app) {
            var st = getStatus(app.bank_status);
            var pct = (app.progress || 0) + '%';
            var card = h('a', { href: app.url, className: 'bre-card' }, [
                h('div', { className: 'bre-card-head' }, [
                    h('div', {}, [
                        h('div', { className: 'bre-card-ref' }, app.name || ''),
                        h('div', { className: 'bre-card-date' }, app.application_date || ''),
                    ]),
                    h('span', { className: 'bre-badge ' + st.cls }, st.label),
                ]),
                h('div', { className: 'bre-card-body' }, [
                    h('div', { className: 'bre-card-prop' }, app.property_name || 'No property assigned'),
                    h('div', { className: 'bre-card-city' }, app.property_city || 'N/A'),
                    h('div', { className: 'bre-card-kv' }, [
                        makeKV('Financing', money(app.financing_amount, app.currency_symbol), 'money'),
                        makeKV('Property Price', money(app.property_price, app.currency_symbol), ''),
                        app.prioritization_number ? makeKV('Prio #', app.prioritization_number, '') : null,
                        app.financing_type ? makeKV('Type', app.financing_type, '') : null,
                    ]),
                ]),
                h('div', { className: 'bre-card-foot' }, [
                    h('span', { className: 'bre-stage-tag' }, app.stage || 'New'),
                    h('div', { className: 'bre-prog-track' }, [
                        h('div', { className: 'bre-prog-bar', style: 'width:' + pct }),
                    ]),
                    h('span', { className: 'bre-prog-pct' }, pct),
                ]),
            ]);
            return card;
        }

        function makeKV(label, value, mod) {
            return h('div', {}, [
                h('div', { className: 'bre-kv-label' }, label),
                h('div', { className: 'bre-kv-val' + (mod ? ' ' + mod : '') }, value || '—'),
            ]);
        }

        /* Page title */
        var header = h('div', { className: 'bre-page-header' }, [
            h('div', {}, [
                h('h2', { className: 'bre-page-title' }, 'My Applications'),
                h('div', { className: 'bre-page-subtitle' }, 'All your financing and property applications'),
            ]),
        ]);

        container.appendChild(header);
        container.appendChild(statsDiv);
        container.appendChild(toolbar);
        container.appendChild(grid);
        renderCards();
    }

    /* ══════════════════════════════════════════════════════════
       DETAIL PAGE
    ══════════════════════════════════════════════════════════ */
    function renderDetailPage(app, container) {
        container.innerHTML = '';

        if (!app) {
            container.appendChild(h('div', { className: 'bre-empty' }, [
                h('div', { style: 'font-size:40px' }, '🔍'),
                h('h3', {}, 'Application not found'),
                h('p', {}, [
                    h('a', { href: '/my/applications' }, '← Return to My Applications'),
                ]),
            ]));
            return;
        }

        var st = getStatus(app.bank_status);
        var pct = (app.progress || 0) + '%';

        var wrap = h('div', { className: 'bre-detail' });

        /* Back link */
        wrap.appendChild(h('a', { href: '/my/applications', className: 'bre-back' }, '← Back to Applications'));

        /* Hero */
        var barFill = h('div', { className: 'bre-hero-bar-fill', style: 'width:' + pct });
        var badges = h('div', { className: 'bre-hero-badges' }, [
            h('span', { className: 'bre-badge ' + st.cls }, st.label),
            h('span', { className: 'bre-stage-chip' }, app.stage || 'New Application'),
            app.prioritization_number ? h('span', { className: 'bre-stage-chip' }, 'Prio # ' + app.prioritization_number) : null,
            app.prioritization_file_number ? h('span', { className: 'bre-stage-chip' }, 'File # ' + app.prioritization_file_number) : null,
        ]);
        var hero = h('div', { className: 'bre-hero' }, [
            h('div', { className: 'bre-hero-ref' }, app.name || ''),
            h('div', { className: 'bre-hero-title' }, app.customer_name || 'Application Detail'),
            badges,
            h('div', { className: 'bre-hero-bar-track' }, [barFill]),
            h('div', { className: 'bre-hero-pct' }, 'Progress: ' + pct),
        ]);
        wrap.appendChild(hero);

        /* Approved / rejected banners */
        if (app.bank_status === 'approved') {
            var txt = '✓ Your application has been Approved.';
            if (app.approved_amount) txt += ' Approved amount: ' + money(app.approved_amount, app.currency_symbol) + '.';
            wrap.appendChild(h('div', { className: 'bre-approved-banner' }, txt));
        }
        if (app.bank_status === 'rejected' && app.rejection_reason) {
            wrap.appendChild(h('div', { className: 'bre-rejected-banner' }, '✕ Rejected: ' + app.rejection_reason));
        }

        /* Section helper */
        function section(title, rows) {
            var kvDiv = h('div', { className: 'bre-sec-body bre-kvgrid' });
            rows.forEach(function(r) {
                if (!r) return;
                kvDiv.appendChild(h('div', {}, [
                    h('div', { className: 'bre-kv-label' }, r[0]),
                    h('div', { className: 'bre-kv-val' + (r[2] ? ' ' + r[2] : '') }, r[1] || '—'),
                ]));
            });
            var sec = h('div', { className: 'bre-section' }, [
                h('div', { className: 'bre-sec-head' }, title),
                kvDiv,
            ]);
            wrap.appendChild(sec);
        }

        section('⏱ Processing Info', [
            ['Real Estate Agent', pin(app.agent)],
            ['Bank Officer',      pin(app.bank_officer)],
            ['Application Date',  pin(app.application_date)],
            ['Submitted On',      pin(app.submission_date) || 'Not yet submitted'],
            ['Decision Date',     pin(app.decision_date) || 'Pending'],
        ]);

        section('🏠 Selected Property', [
            ['Property',     pin(app.property_name)],
            ['Type',         pin(app.property_type)],
            ['City',         pin(app.property_city)],
            ['Project',      pin(app.property_project)],
            ['Sub Project',  pin(app.property_subproject)],
            ['Zone',         pin(app.property_zone)],
            ['Lot',          pin(app.property_lot)],
            ['Block',        pin(app.property_block)],
            ['TF N#',        pin(app.property_tf_no)],
            ['Property ID',  pin(app.property_id_no)],
            ['Listed Price', money(app.property_price, app.currency_symbol), 'big'],
            ['Area (m²)',    (app.property_area || 0) + ' m²'],
        ]);

        section('💰 Financing Request', [
            ['Financing Type',   pin(app.financing_type)],
            ['Amount Required',  money(app.financing_amount, app.currency_symbol), 'big'],
            ['Down Payment',     money(app.down_payment, app.currency_symbol)],
            ['Tenure',           (app.tenure_months || 0) + ' months'],
        ]);

        if (app.bank_status === 'approved' && app.approved_amount) {
            section('✓ Approval Details', [
                ['Approved Amount',  money(app.approved_amount, app.currency_symbol), 'big'],
                ['Approved Tenure',  (app.approved_tenure || 0) + ' months'],
                ['Rate',             (app.approved_rate || 0) + '%'],
                app.conditions ? ['Conditions', app.conditions] : null,
            ]);
        }

        /* Documents */
        if (app.documents && app.documents.length) {
            var docList = h('div', { className: 'bre-sec-body' });
            app.documents.forEach(function(doc) {
                var statusCls = { verified: 'doc-verified', pending: 'doc-pending',
                                  rejected: 'doc-rejected', expired: 'doc-expired' };
                docList.appendChild(h('div', { className: 'bre-doc' }, [
                    h('div', { className: 'bre-doc-ico' }, '📄'),
                    h('span', { className: 'bre-doc-name' }, doc.name || ''),
                    h('span', { className: 'bre-doc-badge ' + (statusCls[doc.status] || 'doc-pending') },
                              doc.status || 'pending'),
                ]));
            });
            var docSec = h('div', { className: 'bre-section' }, [
                h('div', { className: 'bre-sec-head' }, '📄 Documents (' + app.documents.length + ')'),
                docList,
            ]);
            wrap.appendChild(docSec);
        }

        container.appendChild(wrap);
    }

    /* ══════════════════════════════════════════════════════════
       Bootstrap — runs when DOM is ready
    ══════════════════════════════════════════════════════════ */
    function init() {
        var listEl   = document.getElementById('bre-list-root');
        var detailEl = document.getElementById('bre-detail-root');

        if (listEl) {
            try {
                var apps = JSON.parse(listEl.getAttribute('data-records') || '[]');
                renderListPage(apps, listEl);
            } catch(e) {
                console.error('BRE list render error', e);
                listEl.innerHTML = '<p style="color:red;padding:20px">Error loading applications: ' + e.message + '</p>';
            }
        }

        if (detailEl) {
            try {
                var app = JSON.parse(detailEl.getAttribute('data-app') || 'null');
                renderDetailPage(app, detailEl);
            } catch(e) {
                console.error('BRE detail render error', e);
                detailEl.innerHTML = '<p style="color:red;padding:20px">Error loading application: ' + e.message + '</p>';
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
