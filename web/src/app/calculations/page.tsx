import Link from "next/link";

export default function CalculationsPage() {
  return (
    <div className="max-w-[800px] mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-xl font-bold text-gray-900">Bonus Calculations Reference</h1>
        <Link href="/admin" className="text-sm text-blue-600 hover:underline">← Admin</Link>
      </div>

      <div className="space-y-10 text-sm text-gray-700 leading-relaxed">

        {/* Hebrew / Greek / Aramaic */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Hebrew / Greek / Aramaic</h2>
          <p className="mb-3">
            Searches the sermon transcript for patterns that indicate the pastor is referencing the original biblical languages.
            Matches within 20 characters of each other are de-duplicated so the same reference isn&apos;t counted twice.
          </p>
          <h3 className="font-medium text-gray-800 mb-2">5 Detection Patterns:</h3>
          <ol className="list-decimal list-inside space-y-2 ml-2">
            <li>
              <span className="font-medium">Language + noun</span> — <code className="bg-gray-100 px-1 rounded text-xs">the Greek/Hebrew/Aramaic word/term/phrase/root/verb/noun</code>
              <br /><span className="text-gray-500 text-xs ml-5">e.g. &quot;the Greek word <em>agape</em>&quot;</span>
            </li>
            <li>
              <span className="font-medium">In the language</span> — <code className="bg-gray-100 px-1 rounded text-xs">in (the) Greek/Hebrew/Aramaic</code>
              <br /><span className="text-gray-500 text-xs ml-5">e.g. &quot;in the Hebrew, this means...&quot;</span>
            </li>
            <li>
              <span className="font-medium">Language introduction</span> — <code className="bg-gray-100 px-1 rounded text-xs">Greek/Hebrew/Aramaic: or Greek/Hebrew/Aramaic,</code>
              <br /><span className="text-gray-500 text-xs ml-5">When they introduce a translation with punctuation</span>
            </li>
            <li>
              <span className="font-medium">Translation reference</span> — <code className="bg-gray-100 px-1 rounded text-xs">translated from/of</code>
              <br /><span className="text-gray-500 text-xs ml-5">e.g. &quot;translated from the original&quot;</span>
            </li>
            <li>
              <span className="font-medium">Original text</span> — <code className="bg-gray-100 px-1 rounded text-xs">original Greek/Hebrew/language/text</code>
              <br /><span className="text-gray-500 text-xs ml-5">e.g. &quot;the original Greek says...&quot;</span>
            </li>
          </ol>
          <p className="mt-3 text-xs text-gray-500">De-duplication: matches within 20 characters of each other count as one reference.</p>
        </section>

        {/* Church History */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Church History</h2>
          <p className="mb-3">
            Two-pronged approach that scans for historical figures and event/term patterns. De-duplicated within 30 characters
            to avoid double-counting when a name appears near a term (e.g. &quot;Luther&apos;s Reformation&quot; counts as 1, not 2).
          </p>

          <h3 className="font-medium text-gray-800 mb-2">1. Historical Figures (~50 names)</h3>
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <div className="flex flex-wrap gap-2 text-xs">
              {[
                "Augustine","Aquinas","Luther","Calvin","Wesley","Spurgeon","Moody","Whitefield","Edwards",
                "Bonhoeffer","C.S. Lewis","Tozer","Müller","Mueller","Chrysostom","Athanasius","Origen",
                "Tertullian","Polycarp","Ignatius","Irenaeus","Jerome","Ambrose","Anselm","Wycliffe",
                "Tyndale","Huss","Zwingli","Knox","Bunyan","Owen","Baxter","Carey","Judson","Livingstone",
                "Booth","Graham","Schaeffer","Packer","Stott","Lloyd-Jones","Ravenhill","Torrey","Finney",
                "Arminius","Barth","Niebuhr","Tillich",
              ].map((name) => (
                <span key={name} className="bg-white border border-gray-200 rounded px-2 py-1">{name}</span>
              ))}
            </div>
          </div>

          <h3 className="font-medium text-gray-800 mb-2">2. Event &amp; Term Patterns</h3>
          <ul className="list-disc list-inside space-y-2 ml-2">
            <li>
              <span className="font-medium">Church terms</span> — church father, history, council, creed, reformation, revival, awakening, crusade, inquisition
            </li>
            <li>
              <span className="font-medium">Named creeds/confessions</span> — Nicene, Apostles&apos; Creed, Westminster, Heidelberg, Augsburg
            </li>
            <li>
              <span className="font-medium">Church eras</span> — early church, medieval church, Protestant, Catholic church, Orthodox church
            </li>
            <li>
              <span className="font-medium">Ordinal events</span> — First/Second/Third/Great century, awakening, or council
            </li>
            <li>
              <span className="font-medium">Century references</span> — &quot;3rd century&quot;, &quot;16th century&quot;, etc.
            </li>
          </ul>
          <p className="mt-3 text-xs text-gray-500">De-duplication: matches within 30 characters of each other count as one reference.</p>
        </section>

        {/* Bonus Formula */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Bonus Point Formula</h2>
          <p className="mb-3">Each row on the admin page calculates its total independently:</p>
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <p><code className="bg-white border border-gray-200 rounded px-2 py-1 text-xs">Row Total = min(Max, |Count × Bonus|) × sign(Count × Bonus)</code></p>
            <ul className="list-disc list-inside space-y-1 text-xs text-gray-600 ml-2">
              <li><strong>Count</strong> — number of occurrences (auto-detected or manual)</li>
              <li><strong>Bonus</strong> — per-occurrence weight from the slider (±Max range)</li>
              <li><strong>Max</strong> — cap on the row&apos;s total contribution (default: 5)</li>
            </ul>
            <p className="text-xs text-gray-600">
              The <strong>Total Bonus</strong> is the sum of all row totals. This value is added to the PSR score to produce the <strong>Total Score</strong>:
            </p>
            <p><code className="bg-white border border-gray-200 rounded px-2 py-1 text-xs">Total Score = PSR + Total Bonus (clamped 0–100)</code></p>
          </div>
        </section>

        {/* Word Search */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Word Search Rows</h2>
          <p>
            The first 3 rows are free-text word searches. Type any word and the system counts exact whole-word matches
            (case-insensitive) in the transcript. The first row defaults to &quot;Jesus&quot;. Special characters in the
            search word are escaped so punctuation is matched literally.
          </p>
        </section>

        {/* Biblical Accuracy & Time in the Word */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Biblical Accuracy &amp; Time in the Word</h2>
          <p>
            These rows pull their scores directly from the sermon&apos;s AI-generated category scores (the same values shown
            on the sermon detail page). The count field shows the category score (read-only) and the bonus slider lets you
            apply a manual adjustment. These are useful when you believe the AI over- or under-scored a particular category.
          </p>
        </section>

        {/* Score Color Thresholds */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Score Color Thresholds</h2>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-red-500" />
              <span>Below 60</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-yellow-500" />
              <span>60 – 73.9</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-green-500" />
              <span>74+</span>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
