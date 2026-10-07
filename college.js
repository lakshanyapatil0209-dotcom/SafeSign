let previousSnapshot = "";


/* =========================================================
   SECURITY ESCAPE
========================================================= */

function esc(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* =========================================================
   STATUS BADGE
========================================================= */

function statusHTML(status) {

    if (status === "VERIFIED") {
        return `
            <span class="college-status verified">
                <span>✓</span>
                VERIFIED
            </span>
        `;
    }

    if (status === "FAILED") {
        return `
            <span class="college-status failed">
                <span>!</span>
                FAILED
            </span>
        `;
    }

    return `
        <span class="college-status pending">
            <span>●</span>
            PENDING
        </span>
    `;
}


/* =========================================================
   LOAD DOCUMENTS
========================================================= */

async function loadDocuments() {

    const container = document.getElementById("documents");

    try {

        const res = await fetch(
            "/api/college/documents",
            {
                cache: "no-store",
                credentials: "same-origin"
            }
        );


        /* -----------------------------------------
           CHECK HTTP RESPONSE
        ----------------------------------------- */

        if (!res.ok) {

            throw new Error(
                `Server returned HTTP ${res.status}`
            );
        }


        const data = await res.json();

        const docs = data.documents || [];


        /* -----------------------------------------
           UPDATE COUNTERS
        ----------------------------------------- */

        const pending =
            docs.filter(d => d.status === "PENDING").length;

        const verified =
            docs.filter(d => d.status === "VERIFIED").length;

        const failed =
            docs.filter(d => d.status === "FAILED").length;


        document.getElementById(
            "pendingCount"
        ).textContent = pending;

        document.getElementById(
            "verifiedCount"
        ).textContent = verified;

        document.getElementById(
            "failedCount"
        ).textContent = failed;


        /* -----------------------------------------
           DETECT CHANGES
        ----------------------------------------- */

        const snapshot = JSON.stringify(
            docs.map(d => [
                d.document_id,
                d.status
            ])
        );


        if (
            previousSnapshot &&
            snapshot !== previousSnapshot
        ) {

            const newlyVerified =
                docs.some(
                    d => d.status === "VERIFIED"
                );

            if (newlyVerified) {

                showToast(
                    "🟢 Document verified successfully."
                );
            }
        }


        previousSnapshot = snapshot;


        /* -----------------------------------------
           NO DOCUMENTS
        ----------------------------------------- */

        if (!docs.length) {

            container.innerHTML = `
                <div class="college-empty-state">

                    <div class="college-empty-icon">
                        ◫
                    </div>

                    <h3>
                        No Pending Submissions
                    </h3>

                    <p>
                        Waiting for a parent to submit
                        a digitally signed college document.
                    </p>

                    <span class="college-waiting">
                        ● SYSTEM IS LIVE
                    </span>

                </div>
            `;

            return;
        }


        /* -----------------------------------------
           DOCUMENT TABLE
        ----------------------------------------- */

        container.innerHTML = `

            <div class="college-document-table">

                <div class="college-table-row college-table-head">

                    <div>DOCUMENT</div>
                    <div>STUDENT</div>
                    <div>PARENT</div>
                    <div>SUBMITTED</div>
                    <div>STATUS</div>
                    <div>ACTION</div>

                </div>


                ${docs.map(d => `

                    <div class="college-table-row">

                        <!-- DOCUMENT -->

                        <div class="college-document-cell">

                            <div class="document-file-icon">
                                ▣
                            </div>

                            <div>

                                <strong>
                                    ${esc(d.document_id)}
                                </strong>

                                <small>
                                    Digital document
                                </small>

                            </div>

                        </div>


                        <!-- STUDENT -->

                        <div class="college-student-cell">

                            <strong>
                                ${esc(d.student_name)}
                            </strong>

                            <small>
                                ${esc(d.student_id)}
                            </small>

                        </div>


                        <!-- PARENT -->

                        <div class="college-parent-cell">

                            ${esc(d.parent_name)}

                        </div>


                        <!-- CREATED -->

                        <div class="college-created-cell">

                            ${esc(d.created_at)}

                        </div>


                        <!-- STATUS -->

                        <div>

                            ${statusHTML(d.status)}

                        </div>


                        <!-- ACTION -->

                        <div class="college-action-cell">

                            <button
                                class="college-verify-btn"
                                onclick="verifyDocument('${esc(d.document_id)}')"
                            >

                                ${d.status === "VERIFIED"
                                    ? "↻ RECHECK"
                                    : "✓ VERIFY"
                                }

                            </button>


                            <a
                                class="college-view-btn"
                                target="_blank"
                                href="/documents/${encodeURIComponent(d.document_id)}/file"
                            >
                                View
                            </a>

                        </div>

                    </div>

                `).join("")}

            </div>
        `;


    } catch (err) {

        console.error(
            "College dashboard error:",
            err
        );


        /*
         * IMPORTANT:
         * Instead of silently showing a blank page,
         * show the actual problem on screen.
         */

        container.innerHTML = `

            <div class="college-error-state">

                <div class="college-error-icon">
                    !
                </div>

                <h3>
                    Unable to Load Verification Queue
                </h3>

                <p>
                    The dashboard could not connect
                    to the shared backend.
                </p>

                <small>
                    ${esc(err.message)}
                </small>

                <button
                    class="college-retry-btn"
                    onclick="loadDocuments()"
                >
                    ↻ Try Again
                </button>

            </div>

        `;
    }
}


/* =========================================================
   VERIFY DOCUMENT
========================================================= */

async function verifyDocument(documentId) {

    try {

        showToast(
            "⏳ Verifying document..."
        );


        const res = await fetch(
            `/api/college/verify/${encodeURIComponent(documentId)}`,
            {
                method: "POST",
                credentials: "same-origin"
            }
        );


        if (!res.ok) {

            throw new Error(
                `Verification request failed (${res.status})`
            );
        }


        const data = await res.json();


        if (data.ok) {

            showToast(
                "🟢 VERIFIED — SHA-256 and ML-DSA-65 checks passed."
            );

        } else {

            showToast(
                "🔴 VERIFICATION FAILED — " +
                (data.message || "Verification failed.")
            );
        }


        await loadDocuments();


    } catch (err) {

        console.error(
            "Verification error:",
            err
        );


        showToast(
            "⚠️ Verification error — " +
            err.message
        );
    }
}


/* =========================================================
   TOAST
========================================================= */

function showToast(message) {

    const toast =
        document.getElementById("toast");

    if (!toast) return;


    toast.textContent = message;

    toast.classList.add("show");


    setTimeout(() => {

        toast.classList.remove("show");

    }, 4500);
}


/* =========================================================
   START DASHBOARD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadDocuments();

        setInterval(
            loadDocuments,
            2000
        );

    }
);