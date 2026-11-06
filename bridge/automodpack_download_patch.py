"""Pinned-source transformations for the P16 download policy. No game data writes."""

def once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('Upstream anchor is not unique: ' + before[:100])
    return source.replace(before, after)


def manager(source):
    source = once(source, 'MAX_DOWNLOAD_ATTEMPTS = 2;', 'MAX_DOWNLOAD_ATTEMPTS = 1;')
    source = once(source, 'private long bytesDownloaded = 0;', 'private volatile long bytesDownloaded = 0;')
    source = once(source, 'private long bytesToDownload = 0;', 'private volatile long bytesToDownload = 0;')
    source = once(source, 'queuedDownloads.put(hashPathPair, new QueuedDownload(file, size, urls, 0, successCallback, failureCallback));', '''List<String> candidates = new ArrayList<>();
        if (downloadClient != null) candidates.add("host");
        candidates.addAll(new LinkedHashSet<>(urls));
        queuedDownloads.put(hashPathPair, new QueuedDownload(file, size, candidates, 0, successCallback, failureCallback));''')
    source = once(source, '        boolean interrupted = false;', '''        boolean interrupted = false;
        queuedDownload.transferred = 0;
        queuedDownload.windowStart = System.nanoTime();
        queuedDownload.windowBytes = 0;''')
    source = once(source, 'bytesToDownload += queuedDownload.file.toFile().length(); // Add size of the whole file again because we will try to download it again', 'undoAttempt(queuedDownload);')
    source = once(source, '(numberOfIndexes + 1) * MAX_DOWNLOAD_ATTEMPTS', 'numberOfIndexes * MAX_DOWNLOAD_ATTEMPTS - 1')
    start = source.index('            CompletableFuture<Void> future = CompletableFuture.runAsync(')
    end = source.index('\n        }\n    }', start)
    source = source[:start] + '''            CompletableFuture<Void> future = new CompletableFuture<>();
            downloadsInProgress.put(hashAndPath, new DownloadData(future, queuedDownload.file));
            DOWNLOAD_EXECUTOR.execute(() -> {
                try {
                    downloadTask(hashAndPath, queuedDownload);
                    future.complete(null);
                } catch (Exception e) {
                    future.completeExceptionally(e);
                    LOGGER.error("Error while downloading file - {}", queuedDownload.file.getFileName(), e);
                }
            });''' + source[end:]
    # Both native/HTTP methods have the same cache gate.
    needle = 'if (Objects.equals(hashPathPair.hash(), CustomFileUtils.getHash(outFile))) {\n                return;'
    assert source.count(needle) == 2
    source = source.replace(needle, 'if (Objects.equals(hashPathPair.hash(), CustomFileUtils.getHash(outFile))) {\n                accountBytes(queuedDownload, queuedDownload.size, false);\n                return;')
    source = once(source, '''            bytesDownloaded += bytes;
            speedMeter.addDownloadedBytes(bytes);''', '''            accountBytes(queuedDownload, bytes, true);
            checkRate(queuedDownload);''')
    source = once(source, '''                bytesDownloaded += bytesRead;
                speedMeter.addDownloadedBytes(bytesRead);''', '''                accountBytes(queuedDownload, bytesRead, true);
                checkRate(queuedDownload);''')
    source = once(source, '    private URLConnection getHttpConnection', '''    private synchronized void accountBytes(QueuedDownload item, long count, boolean network) {
        bytesDownloaded += count;
        item.transferred += count;
        if (network) speedMeter.addDownloadedBytes(count);
    }

    private synchronized void undoAttempt(QueuedDownload item) {
        bytesDownloaded -= item.transferred;
        item.transferred = 0;
    }

    private void checkRate(QueuedDownload item) {
        // Never reject a slow final source when there is nowhere else to go.
        if (item.attempts >= item.urls.size() - 1) return;
        long now = System.nanoTime();
        long elapsed = now - item.windowStart;
        if (elapsed < 20_000_000_000L) return;
        long bytes = item.transferred - item.windowBytes;
        if (bytes * 1_000_000_000.0 / elapsed < 32 * 1024) {
            throw new IllegalStateException("Source below 32 KiB/s for 20 seconds; trying next source");
        }
        item.windowStart = now;
        item.windowBytes = item.transferred;
    }

    private URLConnection getHttpConnection''')
    source = once(source, '        private int attempts;', '''        private int attempts;
        private long transferred;
        private long windowStart;
        private long windowBytes;''')
    return source


def client(source):
    source = once(source, '    private InetSocketAddress address = null;', '''    private InetSocketAddress address = null;
    private Jsons.ModpackAddresses retryAddresses;
    private byte[] retrySecret;
    private SSLContext retryContext;
    private int desiredConnections;
    private boolean closed;
''')
    source = once(source, '        if (probe.connection.getSocket() != null', '''        retryAddresses = modpackAddresses;
        retrySecret = secretBytes == null ? null : secretBytes.clone();
        retryContext = probe.sslContext;
        desiredConnections = poolSize;

        if (probe.connection.getSocket() != null''')
    start = source.index('        Iterator<Connection> iterator = connections.iterator();')
    end = source.index('\n    }', start)
    source = source[:start] + '''        if (closed) throw new IllegalStateException("Download client closed");
        connections.removeIf(conn -> !conn.isActive());
        for (Connection conn : connections) {
            if (!conn.isBusy()) {
                conn.setBusy(true);
                return conn;
            }
        }
        if (retrySecret != null && connections.size() < desiredConnections) {
            try {
                Connection conn = new Connection(getPreValidationConnection(retryAddresses, retryContext), retrySecret);
                conn.setBusy(true);
                connections.add(conn);
                return conn;
            } catch (IOException e) {
                throw new CompletionException(e);
            }
        }
        throw new IllegalStateException("No available connections");''' + source[end:]
    source = once(source, '''    public void close() {
        for (Connection conn : connections)''', '''    public synchronized void close() {
        closed = true;
        for (Connection conn : connections)''')
    source = once(source, '''    private void finalBlock(Exception exception) {
        try {''', '''    private void finalBlock(Exception exception) {
        if (exception != null) {
            close(); // Never reuse a connection with unread frames after abort/failure.
            return;
        }
        try {''')
    source = once(source, '''            if (exception == null) throw new CompletionException(e);
        } finally {''', '''            close();
            throw new CompletionException(e);
        } finally {''')
    return source
