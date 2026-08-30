import { useState } from "react";

/**
 * One dense table shared by Audit, Halted, Exceptions and Batch Results.
 *
 * 44px rows, 1px borders, no zebra striping — the data density is the feature.
 * Row expansion is inline rather than a modal so the reader never loses their
 * place in the log.
 */
export default function DataTable({ columns, rows, rowKey, renderExpanded, empty = "Nothing to show." }) {
  const [openKey, setOpenKey] = useState(null);
  const expandable = typeof renderExpanded === "function";

  if (!rows || rows.length === 0) {
    return <p className="empty muted">{empty}</p>;
  }

  return (
    <div className="table-wrap">
      <table className="dt">
        <thead>
          <tr>
            {expandable && <th className="dt-toggle" aria-label="Expand" />}
            {columns.map((c) => (
              <th key={c.key} style={c.width ? { width: c.width } : undefined}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const key = rowKey ? rowKey(row, i) : i;
            const open = openKey === key;
            return [
              <tr
                key={key}
                className={expandable ? "dt-row dt-clickable" : "dt-row"}
                onClick={expandable ? () => setOpenKey(open ? null : key) : undefined}
              >
                {expandable && (
                  <td className="dt-toggle mono">{open ? "−" : "+"}</td>
                )}
                {columns.map((c) => (
                  <td key={c.key} className={c.className}>
                    {c.render ? c.render(row) : row[c.key]}
                  </td>
                ))}
              </tr>,
              expandable && open ? (
                <tr key={`${key}-x`} className="dt-expanded">
                  <td colSpan={columns.length + 1}>{renderExpanded(row)}</td>
                </tr>
              ) : null,
            ];
          })}
        </tbody>
      </table>
    </div>
  );
}
