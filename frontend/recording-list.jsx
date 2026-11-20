import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Alert,
  Button,
  Stack,
  Typography,
} from "@mui/material";

import { ThemeProvider } from "@mui/material/styles";

import { recordingThemes } from "./recording-theme.js";
import { RecordingListFilters } from "./recording-list-filters.jsx";
import { RecordingListActions } from "./recording-list-actions.jsx";
import { RecordingListTable } from "./recording-list-table.jsx";

const formatNumber = new Intl.NumberFormat("nl-BE");

async function fetchPage(dataUrl, search, page, signal) {
  const url = new URL(dataUrl, window.location.origin);

  url.search = search;
  url.searchParams.set("page", String(page));

  const response = await fetch(url.href, {
    credentials: "same-origin",
    cache: "no-store",
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error("Opnames laden mislukt.");
  }

  const result = await response.json();

  if (
    !Array.isArray(result.rows) ||
    !Array.isArray(result.matchingItems)
  ) {
    throw new Error("Geen geldige opnamelijst ontvangen.");
  }

  return result;
}

function RecordingListContent({ dataUrl }) {
  const [search, setSearch] = useState(window.location.search);
  const [retry, setRetry] = useState(0);
  const [data, setData] = useState(null);
  const [rows, setRows] = useState([]);
  const [selectedIds, setSelectedIds] = useState(() => new Set());

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [moreError, setMoreError] = useState("");
  const [nextPage, setNextPage] = useState(null);

  const generation = useRef(0);
  const moreBusy = useRef(false);
  const moreController = useRef(null);
  const sentinel = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    const requestId = ++generation.current;

    moreController.current?.abort();
    moreBusy.current = false;

    setLoading(true);
    setLoadingMore(false);
    setError("");
    setMoreError("");
    setSelectedIds(new Set());

    async function load() {
      try {
        const result = await fetchPage(
          dataUrl,
          search,
          1,
          controller.signal
        );

        if (
          requestId !== generation.current ||
          controller.signal.aborted
        ) return;

        setData(result);
        setRows(result.rows);
        setNextPage(result.nextPage);
      } catch {
        if (
          !controller.signal.aborted &&
          requestId === generation.current
        ) {
          setError(
            "De opnames konden niet worden geladen. Probeer opnieuw."
          );
        }
      } finally {
        if (
          !controller.signal.aborted &&
          requestId === generation.current
        ) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      controller.abort();
      moreController.current?.abort();
      generation.current += 1;
    };
  }, [dataUrl, search, retry]);

  useEffect(() => {
    function restoreLocation() {
      setSearch(window.location.search);
      setRetry((value) => value + 1);
    }

    function restorePage(event) {
      if (event.persisted) restoreLocation();
    }

    window.addEventListener("popstate", restoreLocation);
    window.addEventListener("pageshow", restorePage);
    window.addEventListener(
      "signbank:row-updated",
      restoreLocation
    );

    return () => {
      window.removeEventListener("popstate", restoreLocation);
      window.removeEventListener("pageshow", restorePage);
      window.removeEventListener(
        "signbank:row-updated",
        restoreLocation
      );
    };
  }, []);

  function navigate(changes) {
    const url = new URL(window.location.href);

    for (const [key, value] of Object.entries(changes)) {
      if (value === "" || value == null) {
        url.searchParams.delete(key);
      } else {
        url.searchParams.set(key, value);
      }
    }

    url.searchParams.delete("page");

    if (url.href !== window.location.href) {
      window.history.pushState(
        window.history.state,
        "",
        url.href
      );
    }

    if (url.search === search) {
      setRetry((value) => value + 1);
    } else {
      setSearch(url.search);
    }

    setSelectedIds(new Set());

    window.scrollTo({
      top: 0,
      behavior: "auto",
    });
  }

  const loadMore = useCallback(async () => {
    if (
      !data ||
      loading ||
      error ||
      moreBusy.current ||
      nextPage === null
    ) return;

    const controller = new AbortController();
    const requestId = generation.current;

    moreController.current = controller;
    moreBusy.current = true;

    setLoadingMore(true);
    setMoreError("");

    try {
      const result = await fetchPage(
        dataUrl,
        search,
        nextPage,
        controller.signal
      );

      if (
        controller.signal.aborted ||
        requestId !== generation.current
      ) return;

      const allowed = new Set(
        result.matchingItems.map((item) => item.id)
      );

      setRows((current) => {
        const combined = [
          ...current.filter((row) => allowed.has(row.id)),
          ...result.rows,
        ];

        return Array.from(
          new Map(
            combined.map((row) => [row.id, row])
          ).values()
        );
      });

      setSelectedIds((current) => new Set(
        [...current].filter((id) => allowed.has(id))
      ));

      setData(result);
      setNextPage(result.nextPage);
    } catch {
      if (
        !controller.signal.aborted &&
        requestId === generation.current
      ) {
        setMoreError(
          "De volgende opnames konden niet worden geladen."
        );
      }
    } finally {
      if (requestId === generation.current) {
        moreBusy.current = false;
        setLoadingMore(false);
      }
    }
  }, [
    data,
    dataUrl,
    search,
    nextPage,
    loading,
    error,
  ]);

  useEffect(() => {
    if (
      loading ||
      loadingMore ||
      error ||
      moreError ||
      nextPage === null ||
      !sentinel.current ||
      !("IntersectionObserver" in window)
    ) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          observer.disconnect();
          loadMore();
        }
      },
      { rootMargin: "400px" }
    );

    observer.observe(sentinel.current);

    return () => observer.disconnect();
  }, [
    loadMore,
    loading,
    loadingMore,
    error,
    moreError,
    nextPage,
  ]);

  function toggleSelection(id) {
    setSelectedIds((current) => {
      const next = new Set(current);

      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }

      return next;
    });
  }

  function toggleVisible(ids) {
    setSelectedIds((current) => {
      const next = new Set(current);
      const remove = ids.every((id) => next.has(id));

      ids.forEach((id) => {
        if (remove) next.delete(id);
        else next.add(id);
      });

      return next;
    });
  }

  if (!data) {
    return error ? (
      <Alert
        severity="error"
        action={
          <Button onClick={() => setRetry((value) => value + 1)}>
            Opnieuw proberen
          </Button>
        }
      >
        {error}
      </Alert>
    ) : (
      <Typography role="status">
        Opnames laden…
      </Typography>
    );
  }

  const busy = loading || Boolean(error);

  const selectedItems = data.matchingItems.filter(
    (item) => selectedIds.has(item.id)
  );

  return (
    <Stack spacing={2} sx={{ minWidth: 0 }}>
      <Stack
        direction="row"
        useFlexGap
        flexWrap="wrap"
        spacing={2}
        sx={{
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Typography component="h1" variant="h4" fontWeight={700}>
          Opnames
        </Typography>

        <Stack
          direction="row"
          useFlexGap
          flexWrap="wrap"
          spacing={1}
          sx={{ alignItems: "center" }}
        >
          <Typography variant="body2">
            <strong>
              {formatNumber.format(data.filteredCount)} resultaten
            </strong>
            {" / "}
            {formatNumber.format(data.totalCount)} totaal
          </Typography>

          <Button
            href={data.urls.bulkVideoUpload}
            variant="outlined"
          >
            Bulk video-upload
          </Button>

          <Button href={data.urls.importUrls}>
            URL-lijst importeren
          </Button>

          <Button href={data.urls.importGoogleSheet}>
             Google Sheet koppelen
          </Button>

          <Button href={data.urls.syncGoogleSheet}>
            Google Sheet synchroniseren
        </Button>
        </Stack>
      </Stack>

      {loading && (
        <Typography role="status">
          Opnamelijst bijwerken…
        </Typography>
      )}

      {error && (
        <Alert
          severity="error"
          action={
            <Button onClick={() => setRetry((value) => value + 1)}>
              Opnieuw proberen
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      <RecordingListFilters
        data={data}
        onNavigate={navigate}
        loading={busy}
      />

      <RecordingListActions
        data={data}
        selectedItems={selectedItems}
        loading={busy}
        onSelectAll={() => setSelectedIds(
          new Set(
            data.matchingItems.map((item) => item.id)
          )
        )}
        onClearSelection={() => setSelectedIds(new Set())}
      />

      <RecordingListTable
        data={data}
        rows={rows}
        selectedIds={selectedIds}
        loading={busy}
        onToggleSelection={toggleSelection}
        onToggleVisible={toggleVisible}
        onNavigate={navigate}
      />

      <Stack
        ref={sentinel}
        spacing={1}
        sx={{ alignItems: "center", py: 2 }}
      >
        {loadingMore && (
          <Typography role="status">
            Meer opnames laden…
          </Typography>
        )}

        {moreError && (
          <Alert
            severity="error"
            action={
              <Button onClick={loadMore}>
                Opnieuw proberen
              </Button>
            }
          >
            {moreError}
          </Alert>
        )}

        {!loading &&
          !loadingMore &&
          !error &&
          !moreError &&
          nextPage !== null && (
            <Button variant="outlined" onClick={loadMore}>
              Meer opnames laden
            </Button>
          )}

        {!loading &&
          !error &&
          nextPage === null &&
          rows.length > 0 && (
            <Typography variant="body2" color="text.secondary">
              Alle resultaten zijn geladen.
            </Typography>
          )}
      </Stack>
    </Stack>
  );
}

export function RecordingList({
  dataUrl,
  mode = "light",
}) {
  return (
    <ThemeProvider
      theme={recordingThemes[mode] || recordingThemes.light}
    >
      <RecordingListContent dataUrl={dataUrl} />
    </ThemeProvider>
  );
}