import {
  Fragment,
  type ReactElement,
} from "react";

import type { ChatMessage } from "../types/chat";

import ChartRenderer from "./ChartRenderer";

interface MessageProps {
  message: ChatMessage;
}

type TableAlignment =
  | "left"
  | "center"
  | "right";

interface ParsedTable {
  headers: string[];
  alignments: TableAlignment[];
  rows: string[][];
  endIndex: number;
}

function renderInline(text: string) {
  const parts = text.split(
    /(\*\*[^*]+\*\*|`[^`]+`)/g
  );

  return parts.map((part, index) => {
    if (
      part.startsWith("**") &&
      part.endsWith("**")
    ) {
      return (
        <strong key={index}>
          {part.slice(2, -2)}
        </strong>
      );
    }

    if (
      part.startsWith("`") &&
      part.endsWith("`")
    ) {
      return (
        <code key={index}>
          {part.slice(1, -1)}
        </code>
      );
    }

    return (
      <Fragment key={index}>
        {part}
      </Fragment>
    );
  });
}

function splitTableRow(line: string): string[] {
  let value = line.trim();

  if (value.startsWith("|")) {
    value = value.slice(1);
  }

  if (value.endsWith("|")) {
    value = value.slice(0, -1);
  }

  const cells: string[] = [];
  let current = "";
  let escaped = false;

  for (const character of value) {
    if (escaped) {
      if (character === "|") {
        current += "|";
      } else {
        current += `\\${character}`;
      }

      escaped = false;
      continue;
    }

    if (character === "\\") {
      escaped = true;
      continue;
    }

    if (character === "|") {
      cells.push(current.trim());
      current = "";
      continue;
    }

    current += character;
  }

  if (escaped) {
    current += "\\";
  }

  cells.push(current.trim());

  return cells;
}

function getTableAlignment(
  separator: string
): TableAlignment {
  const trimmed = separator.trim();

  const startsWithColon =
    trimmed.startsWith(":");

  const endsWithColon =
    trimmed.endsWith(":");

  if (
    startsWithColon &&
    endsWithColon
  ) {
    return "center";
  }

  if (endsWithColon) {
    return "right";
  }

  return "left";
}

function isTableSeparatorRow(
  line: string
): boolean {
  const cells = splitTableRow(line);

  if (cells.length === 0) {
    return false;
  }

  return cells.every((cell) =>
    /^:?-{3,}:?$/.test(
      cell.trim()
    )
  );
}

function parseTable(
  lines: string[],
  startIndex: number
): ParsedTable | null {
  if (
    startIndex + 1 >=
    lines.length
  ) {
    return null;
  }

  const headerLine =
    lines[startIndex].trim();

  const separatorLine =
    lines[startIndex + 1].trim();

  if (
    !headerLine.includes("|") ||
    !isTableSeparatorRow(
      separatorLine
    )
  ) {
    return null;
  }

  const headers =
    splitTableRow(headerLine);

  const separatorCells =
    splitTableRow(separatorLine);

  if (
    headers.length === 0 ||
    headers.length !==
      separatorCells.length
  ) {
    return null;
  }

  const alignments =
    separatorCells.map(
      getTableAlignment
    );

  const rows: string[][] = [];

  let endIndex =
    startIndex + 2;

  while (
    endIndex < lines.length
  ) {
    const line =
      lines[endIndex].trim();

    if (!line || !line.includes("|")) {
      break;
    }

    const cells =
      splitTableRow(line);

    if (
      cells.length !==
      headers.length
    ) {
      break;
    }

    rows.push(cells);
    endIndex += 1;
  }

  return {
    headers,
    alignments,
    rows,
    endIndex,
  };
}

function MarkdownTable({
  table,
  tableKey,
}: {
  table: ParsedTable;
  tableKey: string;
}) {
  return (
    <div
      className="message-table-wrapper"
      key={tableKey}
    >
      <table className="message-table">
        <thead>
          <tr>
            {table.headers.map(
              (header, index) => (
                <th
                  key={`header-${index}`}
                  style={{
                    textAlign:
                      table.alignments[
                        index
                      ],
                  }}
                >
                  {renderInline(
                    header
                  )}
                </th>
              )
            )}
          </tr>
        </thead>

        <tbody>
          {table.rows.map(
            (row, rowIndex) => (
              <tr
                key={`row-${rowIndex}`}
              >
                {row.map(
                  (cell, cellIndex) => (
                    <td
                      key={`cell-${rowIndex}-${cellIndex}`}
                      style={{
                        textAlign:
                          table.alignments[
                            cellIndex
                          ],
                      }}
                    >
                      {renderInline(
                        cell
                      )}
                    </td>
                  )
                )}
              </tr>
            )
          )}
        </tbody>
      </table>
    </div>
  );
}

function MarkdownContent({
  content,
}: {
  content: string;
}) {
  const lines =
    content.split("\n");

  const blocks: ReactElement[] = [];

  let listItems: string[] = [];

  function flushList() {
    if (!listItems.length) {
      return;
    }

    blocks.push(
      <ul
        key={`list-${blocks.length}`}
      >
        {listItems.map(
          (item, index) => (
            <li key={index}>
              {renderInline(item)}
            </li>
          )
        )}
      </ul>
    );

    listItems = [];
  }

  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      index += 1;
      continue;
    }

    /*
     * Markdown table detection must happen
     * before normal paragraph rendering.
     *
     * A line is considered a table header only
     * when the following line is a valid
     * Markdown separator row.
     */
    const table = parseTable(
      lines,
      index
    );

    if (table) {
      flushList();

      blocks.push(
        <MarkdownTable
          key={`table-${index}`}
          table={table}
          tableKey={`table-${index}`}
        />
      );

      index = table.endIndex;
      continue;
    }

    if (
      trimmed.startsWith("- ") ||
      trimmed.startsWith("* ")
    ) {
      listItems.push(
        trimmed.slice(2)
      );

      index += 1;
      continue;
    }

    flushList();

    if (
      trimmed.startsWith(
        "### "
      )
    ) {
      blocks.push(
        <h3
          key={`h3-${index}`}
        >
          {renderInline(
            trimmed.slice(4)
          )}
        </h3>
      );

      index += 1;
      continue;
    }

    if (
      trimmed.startsWith(
        "## "
      )
    ) {
      blocks.push(
        <h2
          key={`h2-${index}`}
        >
          {renderInline(
            trimmed.slice(3)
          )}
        </h2>
      );

      index += 1;
      continue;
    }

    if (
      trimmed.startsWith(
        "# "
      )
    ) {
      blocks.push(
        <h2
          key={`h1-${index}`}
        >
          {renderInline(
            trimmed.slice(2)
          )}
        </h2>
      );

      index += 1;
      continue;
    }

    blocks.push(
      <p
        key={`p-${index}`}
      >
        {renderInline(trimmed)}
      </p>
    );

    index += 1;
  }

  flushList();

  return (
    <div className="message-content">
      {blocks}
    </div>
  );
}

function AssistantAvatar() {
  return (
    <div
      className="assistant-avatar"
      aria-hidden="true"
    >
      <span className="mini-shape mini-one" />
      <span className="mini-shape mini-two" />
    </div>
  );
}

export default function Message({
  message,
}: MessageProps) {
  const isUser =
    message.role === "user";

  const isChallenge =
    message.messageType ===
    "challenge";

  return (
    <article
      className={`message-row ${
        isUser
          ? "message-row-user"
          : "message-row-assistant"
      } ${
        isChallenge
          ? "message-row-challenge"
          : ""
      }`}
    >
      {!isUser && (
        <AssistantAvatar />
      )}

      <div
        className={`message-body ${
          isUser
            ? "message-body-user"
            : "message-body-assistant"
        }`}
      >
        {!isUser && (
          <div className="message-header">
            <span className="message-role">
              Nexa
            </span>

            {isChallenge && (
              <span className="challenge-label">
                Challenge review
              </span>
            )}
          </div>
        )}

        <MarkdownContent
          content={message.content}
        />

        {!isUser &&
          message.toolsUsed &&
          message.toolsUsed.length >
            0 && (
            <details className="sources">
              <summary>
                Sources ·{" "}
                {message.toolsUsed.length}
              </summary>

              <div className="source-list">
                {message.toolsUsed.map(
                  (tool) => (
                    <span
                      className="source-item"
                      key={tool}
                    >
                      {tool}
                    </span>
                  )
                )}
              </div>
            </details>
          )}

        {!isUser &&
          message.visualization && (
            <div className="message-chart">
              <ChartRenderer
                visualization={
                  message.visualization
                }
              />
            </div>
          )}
      </div>
    </article>
  );
}