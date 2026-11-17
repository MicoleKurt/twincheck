"""Render a comparison as terminal text or one self-contained HTML file."""
import html

MARK = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "info": "INFO"}


def text(result, max_details=8):
    out = ["twincheck  %s -> %s" % (result["source_lang"] or "?", result["target_lang"]),
           "source: %s" % result["source"], "copy:   %s" % result["copy"], ""]
    for r in result["rows"]:
        out.append("[%s] %-30s %s" % (MARK[r["status"]], r["check"], r["summary"]))
        for d in r["details"][:max_details]:
            out.append("         - %s" % d)
        if len(r["details"]) > max_details:
            out.append("         - ... %d more" % (len(r["details"]) - max_details))
    c = result["counts"]
    out += ["", "%d passed, %d warnings, %d failed. %s" % (
        c["pass"], c["warn"], c["fail"], "The copy is ready." if result["ok"] else "The copy is not ready.")]
    return "\n".join(out)


_CSS = """
:root{--bg:#fbfaf7;--ink:#1d1d1b;--mute:#6b6a65;--line:#e4e1d8;--pass:#2f7d4f;--warn:#a86a00;--fail:#b3261e;--info:#4a5b78}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--ink:#eceae4;--mute:#a09e97;--line:#33322e;--pass:#6fcf97;--warn:#f0b24a;--fail:#ff8a80;--info:#9db4d8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}h1{font-size:28px;margin:0 0 4px}
.sub{color:var(--mute);margin:0 0 24px;overflow-wrap:anywhere}.verdict{font-size:20px;font-weight:650;margin:0 0 24px}
.row{border-top:1px solid var(--line);padding:14px 0;display:grid;grid-template-columns:64px 1fr;gap:12px}
.tag{font:650 12px/24px ui-monospace,Consolas,monospace;letter-spacing:.04em}
.pass .tag{color:var(--pass)}.warn .tag{color:var(--warn)}.fail .tag{color:var(--fail)}.info .tag{color:var(--info)}
.name{font-weight:650}.sum{color:var(--mute)}ul{margin:8px 0 0;padding-left:18px;font-size:14px;overflow-wrap:anywhere}
"""


def html_page(result):
    e = html.escape
    rows = []
    for r in result["rows"]:
        details = "".join("<li>%s</li>" % e(d) for d in r["details"])
        rows.append('<div class="row %s"><div class="tag">%s</div><div><div class="name">%s</div>'
                    '<div class="sum">%s</div>%s</div></div>'
                    % (r["status"], MARK[r["status"]], e(r["check"]), e(r["summary"]),
                       "<ul>%s</ul>" % details if details else ""))
    c = result["counts"]
    verdict = "The copy is ready." if result["ok"] else "The copy is not ready."
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>twincheck report</title>"
            "<style>%s</style></head><body><main><h1>twincheck report</h1>"
            "<p class=\"sub\">%s &rarr; %s<br>source: %s<br>copy: %s</p>"
            "<p class=\"verdict\">%s %d passed, %d warnings, %d failed.</p>%s</main></body></html>"
            % (_CSS, e(result["source_lang"] or "?"), e(result["target_lang"]), e(result["source"]),
               e(result["copy"]), verdict, c["pass"], c["warn"], c["fail"], "".join(rows)))
