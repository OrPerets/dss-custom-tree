(function() {
    "use strict";

    var NODE_WIDTH = 264;
    var NODE_HEIGHT = 184;
    var HORIZONTAL_GAP = 76;
    var VERTICAL_GAP = 144;
    var DIAGRAM_PADDING = 68;
    var ZOOM_STEP = 1.14;

    var app = angular.module("employeeOrgTreeApp", []);

    app.controller("EmployeeOrgTreeController", function($scope, $http, $document, $timeout, $window) {
        var webAppConfig = (window.dataiku && typeof window.dataiku.getWebAppConfig === "function")
            ? window.dataiku.getWebAppConfig()
            : {};
        var windowElement = angular.element($window);
        var viewportElement = null;

        $scope.state = {
            mode: "loading",
            treeLoading: false,
            moveSubmitting: false,
            snapshotSaving: false,
            snapshotLoading: false,
            hierarchyExporting: false,
            moveLogExporting: false,
            snapshotsLoading: false,
            backendError: null,
            moveFeedback: null,
            snapshotOptions: [],
            selectedSnapshotPath: "",
            lastSavedPayload: null,
            lastSavedSnapshot: null,
            form: {
                employeeDataset: webAppConfig.default_employee_dataset || null,
                constraintsDataset: webAppConfig.default_constraints_dataset || null,
                snapshotFolder: webAppConfig.snapshot_folder || null
            },
            treePayload: null,
            treeRoot: null,
            selectedNode: null,
            allNodes: [],
            nodeMap: {},
            filterOptions: {
                departments: [],
                locations: [],
                statuses: []
            },
            filters: defaultFilters(),
            ui: {
                filtersExpanded: false,
                sessionExpanded: false
            },
            drag: defaultDragState(),
            diagram: emptyDiagram("Loading the configured hierarchy source."),
            canvas: {
                scale: 1,
                x: 0,
                y: 0,
                minScale: 0.35,
                maxScale: 1.8,
                viewportWidth: 0,
                viewportHeight: 0,
                dragging: false,
                dragStartX: 0,
                dragStartY: 0,
                originX: 0,
                originY: 0,
                hasInteracted: false
            }
        };

        if (window.dataiku && typeof window.dataiku.checkWebAppParameters === "function") {
            window.dataiku.checkWebAppParameters();
        }

        $scope.dismissError = function() {
            $scope.state.backendError = null;
        };

        $scope.dismissMoveFeedback = function() {
            $scope.state.moveFeedback = null;
        };

        $scope.selectNode = function(node, $event) {
            if ($event) {
                $event.stopPropagation();
            }
            if (!node) {
                return;
            }
            $scope.state.selectedNode = node;
        };

        $scope.getManagerLabel = function(node) {
            return node.current_manager_name || node.manager_id || "Root employee";
        };

        $scope.getStatusTone = function(node) {
            var status = ((node && node.employment_status) || "").toLowerCase();
            if (status === "active") {
                return "status-active";
            }
            if (status === "leave" || status === "contractor") {
                return "status-attention";
            }
            return "status-inactive";
        };

        $scope.getCapacityTone = function(node) {
            if (!node || node.max_direct_reports == null) {
                return "capacity-open";
            }
            if (node.capacity_remaining <= 0) {
                return "capacity-full";
            }
            if (node.capacity_remaining === 1) {
                return "capacity-near";
            }
            return "capacity-open";
        };

        $scope.getCapacityLabel = function(node) {
            if (!node) {
                return "";
            }
            return node.direct_reports_count + " / " + (node.max_direct_reports == null ? "\u221e" : node.max_direct_reports) + " reports";
        };

        $scope.getWarningLabel = function(warning) {
            if (!warning) {
                return "";
            }
            if (warning.code === "at_capacity") {
                return "At capacity";
            }
            if (warning.code === "employment_status_attention") {
                return "Status alert";
            }
            return "Warning";
        };

        $scope.getWarningCountLabel = function(node) {
            var count = node && node.warnings ? node.warnings.length : 0;
            if (!count) {
                return "No warnings";
            }
            return count === 1 ? "1 warning" : count + " warnings";
        };

        $scope.getAvatarLabel = function(node) {
            if (!node || !node.full_name) {
                return "?";
            }
            return node.full_name
                .split(/\s+/)
                .filter(Boolean)
                .slice(0, 2)
                .map(function(part) {
                    return part.charAt(0).toUpperCase();
                })
                .join("");
        };

        $scope.getRuleSummary = function(node) {
            if (!node || !node.manager_rule) {
                return "No manager-specific rule";
            }
            return node.manager_rule.rule_note || "Manager rule configured";
        };

        $scope.getVisibleEmployeesLabel = function() {
            if (!$scope.state.diagram.totalCount) {
                return "No employees";
            }
            return $scope.state.diagram.visibleCount + " of " + $scope.state.diagram.totalCount + " visible";
        };

        $scope.canUseSnapshotStorage = function() {
            return !!$scope.state.form.snapshotFolder;
        };

        $scope.getUnsavedMoveCount = function() {
            var currentCount = (($scope.state.treePayload && $scope.state.treePayload.change_log) || []).length;
            var savedCount = (($scope.state.lastSavedPayload && $scope.state.lastSavedPayload.change_log) || []).length;
            return Math.max(0, currentCount - savedCount);
        };

        $scope.isDirty = function() {
            return $scope.getUnsavedMoveCount() > 0;
        };

        $scope.getPendingMovesLabel = function() {
            var count = $scope.getUnsavedMoveCount();
            if (!count) {
                return "No pending moves";
            }
            return count === 1 ? "1 pending move" : count + " pending moves";
        };

        $scope.getLastSavedLabel = function() {
            if ($scope.state.lastSavedSnapshot && $scope.state.lastSavedSnapshot.name) {
                return $scope.state.lastSavedSnapshot.name;
            }
            if ($scope.state.lastSavedPayload) {
                return "Current baseline";
            }
            return "Not saved yet";
        };

        $scope.getCanvasTransform = function() {
            return {
                width: $scope.state.diagram.width + "px",
                height: $scope.state.diagram.height + "px",
                transform: "translate(" + $scope.state.canvas.x + "px, " + $scope.state.canvas.y + "px) scale(" + $scope.state.canvas.scale + ")"
            };
        };

        $scope.getNodeStyle = function(renderNode) {
            return {
                left: renderNode.x + "px",
                top: renderNode.y + "px",
                width: NODE_WIDTH + "px",
                "--node-accent": renderNode.accentColor
            };
        };

        $scope.getNodeClassMap = function(renderNode) {
            var preview = $scope.state.drag.preview;
            var isHoverTarget = preview && $scope.state.drag.hoverTargetId === renderNode.employee_id;

            return {
                "org-node--selected": $scope.state.selectedNode && $scope.state.selectedNode.employee_id === renderNode.employee_id,
                "org-node--match": renderNode.match,
                "org-node--warning": renderNode.data.warnings.length,
                "org-node--drag-source": $scope.state.drag.employeeId === renderNode.employee_id,
                "org-node--drop-valid": isHoverTarget && preview.valid,
                "org-node--drop-invalid": isHoverTarget && !preview.valid
            };
        };

        $scope.loadOrgTree = function() {
            $scope.state.treeLoading = true;
            $scope.dismissError();
            $scope.dismissMoveFeedback();
            clearDragState();

            $http.post(getWebAppBackendUrl("validate-input"), buildRequestPayload())
                .then(function() {
                    return $http.post(getWebAppBackendUrl("load-org-tree"), buildRequestPayload());
                })
                .then(function(response) {
                    $scope.state.treeLoading = false;
                    initializeWorkspace(response.data, {
                        fitToScreen: true,
                        resetFilters: true,
                        updateSavedBaseline: true,
                        snapshotInfo: null
                    });
                }, function(error) {
                    $scope.state.treeLoading = false;
                    if (!$scope.state.treePayload) {
                        $scope.state.mode = "config-error";
                    }
                    handleBackendError(error, "Unable to load the employee org tree.");
                });
        };

        $scope.applyFilters = function() {
            rebuildDiagram(false);
        };

        $scope.resetFilters = function() {
            $scope.state.filters = defaultFilters();
            rebuildDiagram(true);
        };

        $scope.toggleFilters = function() {
            $scope.state.ui.filtersExpanded = !$scope.state.ui.filtersExpanded;
            $timeout(function() {
                attachViewport();
                fitDiagramToViewport();
            });
        };

        $scope.getActiveFilterCount = function() {
            return countActiveFilters($scope.state.filters);
        };

        $scope.getFilterSummaryLabel = function() {
            var filters = $scope.state.filters || defaultFilters();
            var labels = [];

            if (filters.search && filters.search.trim()) {
                labels.push("Search: " + filters.search.trim());
            }
            if (filters.department) {
                labels.push("Department: " + filters.department);
            }
            if (filters.location) {
                labels.push("Location: " + filters.location);
            }
            if (filters.status) {
                labels.push("Status: " + filters.status);
            }
            if (filters.onlyWarnings) {
                labels.push("Warnings only");
            }

            if (!labels.length) {
                return "No active filters";
            }

            if (labels.length > 2) {
                return labels.slice(0, 2).join(" / ") + " / +" + (labels.length - 2) + " more";
            }

            return labels.join(" / ");
        };

        $scope.resetUnsavedMoves = function() {
            if (!$scope.state.lastSavedPayload) {
                $scope.loadOrgTree();
                return;
            }

            clearDragState();
            $scope.dismissError();
            $scope.dismissMoveFeedback();
            initializeWorkspace(angular.copy($scope.state.lastSavedPayload), {
                preserveFilters: true,
                fitToScreen: false,
                selectedEmployeeId: $scope.state.selectedNode ? $scope.state.selectedNode.employee_id : null,
                updateSavedBaseline: true,
                snapshotInfo: $scope.state.lastSavedSnapshot
            });
        };

        $scope.saveSnapshot = function() {
            if (!$scope.state.treePayload || $scope.state.snapshotSaving) {
                return;
            }

            $scope.state.snapshotSaving = true;
            $scope.dismissError();

            $http.post(getWebAppBackendUrl("save-snapshot"), angular.extend({}, buildRequestPayload(), {
                snapshot_folder: $scope.state.form.snapshotFolder,
                change_log: angular.copy(getCurrentChangeLog())
            }))
                .then(function(response) {
                    var data = response.data || {};

                    $scope.state.snapshotSaving = false;
                    initializeWorkspace(data.payload, {
                        preserveFilters: true,
                        fitToScreen: false,
                        selectedEmployeeId: $scope.state.selectedNode ? $scope.state.selectedNode.employee_id : null,
                        updateSavedBaseline: true,
                        snapshotInfo: data.snapshot
                    });
                    $scope.state.moveFeedback = {
                        tone: "success",
                        title: "Baseline saved",
                        message: (data.snapshot && data.snapshot.name ? data.snapshot.name : "Snapshot") + " saved successfully.",
                        issues: data.snapshot && data.snapshot.storage_label
                            ? ["Storage: " + data.snapshot.storage_label]
                            : []
                    };
                    loadSnapshots(data.snapshot ? data.snapshot.path : null);
                }, function(error) {
                    $scope.state.snapshotSaving = false;
                    handleBackendError(error, "Unable to save the current org snapshot.");
                });
        };

        $scope.loadSnapshot = function() {
            if (!$scope.state.selectedSnapshotPath || $scope.state.snapshotLoading) {
                return;
            }

            $scope.state.snapshotLoading = true;
            $scope.dismissError();
            clearDragState();

            $http.post(getWebAppBackendUrl("load-snapshot"), angular.extend({}, buildRequestPayload(), {
                snapshot_folder: $scope.state.form.snapshotFolder,
                snapshot_path: $scope.state.selectedSnapshotPath
            }))
                .then(function(response) {
                    var data = response.data || {};

                    $scope.state.snapshotLoading = false;
                    initializeWorkspace(data.payload, {
                        preserveFilters: true,
                        fitToScreen: true,
                        updateSavedBaseline: true,
                        snapshotInfo: data.snapshot
                    });
                    $scope.state.moveFeedback = {
                        tone: "success",
                        title: "Baseline loaded",
                        message: (data.snapshot && data.snapshot.name ? data.snapshot.name : "Snapshot") + " loaded successfully.",
                        issues: []
                    };
                    loadSnapshots($scope.state.selectedSnapshotPath);
                }, function(error) {
                    $scope.state.snapshotLoading = false;
                    handleBackendError(error, "Unable to load the selected snapshot.");
                });
        };

        $scope.exportHierarchy = function() {
            if ($scope.state.hierarchyExporting) {
                return;
            }

            $scope.state.hierarchyExporting = true;
            $scope.dismissError();

            $http.post(getWebAppBackendUrl("export-flat-table"), angular.extend({}, buildRequestPayload(), {
                change_log: angular.copy(getCurrentChangeLog())
            }))
                .then(function(response) {
                    $scope.state.hierarchyExporting = false;
                    downloadFile(response.data);
                    $scope.state.moveFeedback = {
                        tone: "success",
                        title: "Hierarchy exported",
                        message: "The current hierarchy export is ready.",
                        issues: []
                    };
                }, function(error) {
                    $scope.state.hierarchyExporting = false;
                    handleBackendError(error, "Unable to export the current hierarchy.");
                });
        };

        $scope.exportMoveLog = function() {
            if ($scope.state.moveLogExporting) {
                return;
            }

            $scope.state.moveLogExporting = true;
            $scope.dismissError();

            $http.post(getWebAppBackendUrl("export-move-log"), {
                change_log: angular.copy(getCurrentChangeLog())
            })
                .then(function(response) {
                    $scope.state.moveLogExporting = false;
                    downloadFile(response.data);
                    $scope.state.moveFeedback = {
                        tone: "success",
                        title: "Move log exported",
                        message: "The move log export is ready.",
                        issues: []
                    };
                }, function(error) {
                    $scope.state.moveLogExporting = false;
                    handleBackendError(error, "Unable to export the move log.");
                });
        };

        $scope.zoomIn = function() {
            zoomAtViewportCenter(ZOOM_STEP);
        };

        $scope.zoomOut = function() {
            zoomAtViewportCenter(1 / ZOOM_STEP);
        };

        $scope.fitToScreen = function() {
            fitDiagramToViewport();
        };

        $scope.focusSelectedNode = function() {
            focusNode($scope.state.selectedNode);
        };

        $scope.toggleSession = function() {
            $scope.state.ui.sessionExpanded = !$scope.state.ui.sessionExpanded;
            $timeout(function() {
                attachViewport();
                fitDiagramToViewport();
            });
        };

        $scope.beginCanvasPan = function($event) {
            if ($scope.state.drag.employeeId || !$scope.state.diagram.nodes.length || isInteractiveTarget($event.target)) {
                return;
            }

            $scope.state.canvas.dragging = true;
            $scope.state.canvas.dragStartX = $event.clientX;
            $scope.state.canvas.dragStartY = $event.clientY;
            $scope.state.canvas.originX = $scope.state.canvas.x;
            $scope.state.canvas.originY = $scope.state.canvas.y;
            $scope.state.canvas.hasInteracted = true;

            if ($event.preventDefault) {
                $event.preventDefault();
            }
        };

        $scope.startNodeDrag = function(employeeId) {
            if ($scope.state.moveSubmitting || !employeeId || !$scope.state.nodeMap[employeeId]) {
                return;
            }

            clearDragState();
            $scope.state.drag.employeeId = employeeId;
            $scope.state.selectedNode = $scope.state.nodeMap[employeeId];
            $scope.state.moveFeedback = {
                tone: "info",
                title: "Move preview",
                message: "Drag this employee onto a new manager to validate and apply the reassignment.",
                issues: []
            };
        };

        $scope.endNodeDrag = function() {
            if ($scope.state.moveFeedback && $scope.state.moveFeedback.tone === "info") {
                $scope.state.moveFeedback = null;
            }
            clearDragState();
        };

        $scope.updateDropTarget = function(targetEmployeeId) {
            if (!$scope.state.drag.employeeId) {
                return false;
            }

            $scope.state.drag.hoverTargetId = targetEmployeeId;
            $scope.state.drag.preview = buildMovePreview($scope.state.drag.employeeId, targetEmployeeId);
            return !!($scope.state.drag.preview && $scope.state.drag.preview.valid);
        };

        $scope.completeDrop = function(targetEmployeeId) {
            var preview = buildMovePreview($scope.state.drag.employeeId, targetEmployeeId);
            var draggedEmployeeId = $scope.state.drag.employeeId;

            if (!draggedEmployeeId) {
                clearDragState();
                return;
            }

            if (!preview.valid) {
                $scope.state.moveFeedback = {
                    tone: "error",
                    title: "Move rejected",
                    message: preview.message,
                    issues: []
                };
                clearDragState();
                return;
            }

            $scope.state.moveSubmitting = true;
            $scope.dismissError();

            $http.post(getWebAppBackendUrl("move-employee"), angular.extend({}, buildRequestPayload(), {
                employee_id: draggedEmployeeId,
                new_manager_id: targetEmployeeId,
                change_log: angular.copy(($scope.state.treePayload && $scope.state.treePayload.change_log) || [])
            }))
                .then(function(response) {
                    var payload = response.data || {};
                    var latestEntry = (payload.change_log || [])[payload.change_log.length - 1];

                    $scope.state.moveSubmitting = false;
                    clearDragState();
                    initializeWorkspace(payload, {
                        preserveFilters: true,
                        selectedEmployeeId: draggedEmployeeId,
                        fitToScreen: false,
                        updateSavedBaseline: false
                    });
                    $scope.state.moveFeedback = {
                        tone: "success",
                        title: "Move applied",
                        message: latestEntry
                            ? latestEntry.employee_name + " now reports to " + latestEntry.new_manager_name + "."
                            : "Employee move applied successfully.",
                        issues: latestEntry && latestEntry.validation_note ? [latestEntry.validation_note] : []
                    };

                    $timeout(function() {
                        focusNode($scope.state.nodeMap[draggedEmployeeId]);
                    });
                }, function(error) {
                    $scope.state.moveSubmitting = false;
                    clearDragState();
                    handleMoveError(error);
                });
        };

        initialize();
        $document.on("mousemove", onDocumentMouseMove);
        $document.on("mouseup", stopCanvasPan);
        windowElement.on("resize", onWindowResize);

        function initialize() {
            if (!$scope.state.form.employeeDataset) {
                $scope.state.mode = "config-error";
                $scope.state.backendError = {
                    title: "Input workforce dataset required",
                    message: "Configure the required input workforce dataset in the Dataiku webapp settings.",
                    issues: []
                };
                return;
            }

            $scope.loadOrgTree();
        }

        function initializeWorkspace(payload, options) {
            var graph = buildGraph(payload.nodes || [], payload.meta ? payload.meta.root_employee_id : null);
            var effectiveOptions = options || {};
            var selectedEmployeeId = effectiveOptions.selectedEmployeeId;

            $scope.state.treePayload = payload;
            $scope.state.treeRoot = graph.root;
            $scope.state.nodeMap = graph.nodesById;
            $scope.state.allNodes = graph.nodes;
            $scope.state.filterOptions = collectFilterOptions(graph.nodes);
            $scope.state.mode = "workspace";

            if (effectiveOptions.resetFilters) {
                $scope.state.filters = defaultFilters();
            } else if (!effectiveOptions.preserveFilters) {
                $scope.state.filters = angular.copy($scope.state.filters || defaultFilters());
            }

            $scope.state.selectedNode = selectedEmployeeId
                ? graph.nodesById[selectedEmployeeId] || graph.root
                : graph.root;

            if (effectiveOptions.updateSavedBaseline !== false) {
                setSavedBaseline(payload, effectiveOptions.snapshotInfo || null);
            }

            loadSnapshots(effectiveOptions.preferredSnapshotPath || $scope.state.selectedSnapshotPath);

            rebuildDiagram(effectiveOptions.fitToScreen !== false);
        }

        function buildRequestPayload() {
            return {
                use_demo: false,
                employee_dataset: $scope.state.form.employeeDataset,
                constraints_dataset: $scope.state.form.constraintsDataset || null
            };
        }

        function collectFilterOptions(nodes) {
            return {
                departments: extractUniqueValues(nodes, "department"),
                locations: extractUniqueValues(nodes, "location"),
                statuses: extractUniqueValues(nodes, "employment_status")
            };
        }

        function extractUniqueValues(nodes, key) {
            var seen = {};

            nodes.forEach(function(node) {
                if (node[key]) {
                    seen[node[key]] = true;
                }
            });

            return Object.keys(seen).sort(function(left, right) {
                return left.localeCompare(right);
            });
        }

        function buildGraph(nodes, rootEmployeeId) {
            var nodesById = {};
            var orderedNodes = [];

            nodes.forEach(function(node) {
                var graphNode = angular.extend({}, node, {
                    children: [],
                    parent: null
                });
                nodesById[graphNode.employee_id] = graphNode;
                orderedNodes.push(graphNode);
            });

            orderedNodes.forEach(function(node) {
                node.children = (node.children_ids || [])
                    .map(function(childId) {
                        var child = nodesById[childId];
                        if (child) {
                            child.parent = node;
                        }
                        return child;
                    })
                    .filter(Boolean);
            });

            return {
                root: nodesById[rootEmployeeId] || null,
                nodesById: nodesById,
                nodes: orderedNodes
            };
        }

        function rebuildDiagram(shouldFit) {
            var filterResult = collectFilteredNodes();
            var selectedNode = $scope.state.selectedNode;

            $scope.state.diagram = buildDiagram(filterResult);

            if (!$scope.state.diagram.nodes.length) {
                $scope.state.selectedNode = null;
            } else if ($scope.state.diagram.visibleLookup && selectedNode && !$scope.state.diagram.visibleLookup[selectedNode.employee_id]) {
                $scope.state.selectedNode = $scope.state.diagram.firstVisibleNode || $scope.state.treeRoot || null;
            } else if (!$scope.state.selectedNode) {
                $scope.state.selectedNode = $scope.state.diagram.firstVisibleNode || null;
            }

            if ($scope.state.drag.employeeId && !$scope.state.nodeMap[$scope.state.drag.employeeId]) {
                clearDragState();
            } else if ($scope.state.drag.employeeId && $scope.state.drag.hoverTargetId) {
                $scope.state.drag.preview = buildMovePreview($scope.state.drag.employeeId, $scope.state.drag.hoverTargetId);
            }

            $timeout(function() {
                attachViewport();
                if (shouldFit || !$scope.state.canvas.hasInteracted) {
                    fitDiagramToViewport();
                }
            });
        }

        function collectFilteredNodes() {
            var filters = $scope.state.filters;
            var nodes = $scope.state.allNodes;
            var hasFilters = hasActiveFilters(filters);
            var visibleLookup = {};
            var matchLookup = {};
            var matchedIds = [];

            if (!hasFilters) {
                nodes.forEach(function(node) {
                    visibleLookup[node.employee_id] = true;
                });

                return {
                    hasFilters: false,
                    visibleLookup: visibleLookup,
                    matchLookup: {},
                    matchedIds: nodes.map(function(node) { return node.employee_id; }),
                    totalCount: nodes.length
                };
            }

            nodes.forEach(function(node) {
                if (nodeMatchesFilters(node, filters)) {
                    matchedIds.push(node.employee_id);
                    matchLookup[node.employee_id] = true;
                    markAncestorsVisible(node, visibleLookup);
                    visibleLookup[node.employee_id] = true;
                }
            });

            return {
                hasFilters: true,
                visibleLookup: visibleLookup,
                matchLookup: matchLookup,
                matchedIds: matchedIds,
                totalCount: nodes.length
            };
        }

        function hasActiveFilters(filters) {
            return countActiveFilters(filters) > 0;
        }

        function countActiveFilters(filters) {
            var currentFilters = filters || defaultFilters();
            var count = 0;

            if (currentFilters.search && currentFilters.search.trim()) {
                count += 1;
            }
            if (currentFilters.department) {
                count += 1;
            }
            if (currentFilters.location) {
                count += 1;
            }
            if (currentFilters.status) {
                count += 1;
            }
            if (currentFilters.onlyWarnings) {
                count += 1;
            }

            return count;
        }

        function nodeMatchesFilters(node, filters) {
            var search = (filters.search || "").trim().toLowerCase();
            var searchHit = !search || [
                node.full_name,
                node.employee_id,
                node.job_title
            ].join(" ").toLowerCase().indexOf(search) !== -1;
            var departmentHit = !filters.department || node.department === filters.department;
            var locationHit = !filters.location || node.location === filters.location;
            var statusHit = !filters.status || node.employment_status === filters.status;
            var warningHit = !filters.onlyWarnings || !!(node.warnings && node.warnings.length);

            return searchHit && departmentHit && locationHit && statusHit && warningHit;
        }

        function markAncestorsVisible(node, visibleLookup) {
            var current = node;

            while (current) {
                visibleLookup[current.employee_id] = true;
                current = current.parent;
            }
        }

        function buildDiagram(filterResult) {
            var root = $scope.state.treeRoot;
            var nodes = [];
            var links = [];
            var nodeLookup = {};
            var leafIndex = 0;
            var maxRight = 0;
            var maxBottom = 0;

            if (!root || !filterResult.visibleLookup[root.employee_id]) {
                return emptyDiagram(
                    filterResult.hasFilters
                        ? "No employees match the current search and filter selection."
                        : "No hierarchy records are available in the configured source."
                );
            }

            traverse(root, 0);

            return {
                width: Math.max(maxRight + DIAGRAM_PADDING, NODE_WIDTH + (DIAGRAM_PADDING * 2)),
                height: Math.max(maxBottom + DIAGRAM_PADDING, NODE_HEIGHT + (DIAGRAM_PADDING * 2)),
                nodes: nodes,
                links: links,
                visibleCount: nodes.length,
                totalCount: filterResult.totalCount,
                matchedCount: filterResult.matchedIds.length,
                emptyMessage: "",
                visibleLookup: filterResult.visibleLookup,
                firstVisibleNode: nodes.length ? nodes[0].data : null,
                byId: nodeLookup
            };

            function traverse(node, depth) {
                if (!filterResult.visibleLookup[node.employee_id]) {
                    return null;
                }

                var childLayouts = [];
                node.children.forEach(function(child) {
                    var childLayout = traverse(child, depth + 1);
                    if (childLayout) {
                        childLayouts.push(childLayout);
                    }
                });

                var centerX;
                if (!childLayouts.length) {
                    centerX = DIAGRAM_PADDING + (leafIndex * (NODE_WIDTH + HORIZONTAL_GAP)) + (NODE_WIDTH / 2);
                    leafIndex += 1;
                } else {
                    centerX = (childLayouts[0].centerX + childLayouts[childLayouts.length - 1].centerX) / 2;
                }

                var topY = DIAGRAM_PADDING + (depth * (NODE_HEIGHT + VERTICAL_GAP));
                var renderNode = {
                    employee_id: node.employee_id,
                    x: centerX - (NODE_WIDTH / 2),
                    y: topY,
                    centerX: centerX,
                    centerY: topY + (NODE_HEIGHT / 2),
                    data: node,
                    accentColor: getDepartmentAccent(node.department),
                    match: !!filterResult.matchLookup[node.employee_id]
                };

                nodes.push(renderNode);
                nodeLookup[node.employee_id] = renderNode;
                maxRight = Math.max(maxRight, renderNode.x + NODE_WIDTH);
                maxBottom = Math.max(maxBottom, renderNode.y + NODE_HEIGHT);

                childLayouts.forEach(function(childLayout) {
                    links.push({
                        key: node.employee_id + "-" + childLayout.employee_id,
                        path: buildLinkPath(centerX, topY + NODE_HEIGHT, childLayout.centerX, childLayout.y)
                    });
                });

                return {
                    employee_id: node.employee_id,
                    centerX: centerX,
                    y: topY
                };
            }
        }

        function buildLinkPath(startX, startY, endX, endY) {
            var midY = startY + ((endY - startY) / 2);
            return [
                "M", startX, startY,
                "V", midY,
                "H", endX,
                "V", endY
            ].join(" ");
        }

        function buildMovePreview(employeeId, targetEmployeeId) {
            var employee = $scope.state.nodeMap[employeeId];
            var targetManager = $scope.state.nodeMap[targetEmployeeId];
            var rule = targetManager && targetManager.manager_rule;

            if (!employee || !targetManager) {
                return previewResult(false, "Move unavailable", "The selected employee or manager is missing from the current tree.");
            }

            if (employee.manager_id == null) {
                return previewResult(false, "Move blocked", "The root employee cannot be moved under another manager.");
            }

            if (employee.employee_id === targetManager.employee_id) {
                return previewResult(false, "Move blocked", "An employee cannot report to themselves.");
            }

            if (employee.manager_id === targetManager.employee_id) {
                return previewResult(false, "No change", employee.full_name + " already reports to " + targetManager.full_name + ".");
            }

            if (isDescendant(employee.employee_id, targetManager.employee_id)) {
                return previewResult(false, "Move blocked", "This move would create a reporting cycle because the target manager is inside the employee's subtree.");
            }

            if (!targetManager.can_be_manager) {
                return previewResult(false, "Move blocked", targetManager.full_name + " cannot receive direct reports.");
            }

            if ((targetManager.employment_status || "").toLowerCase() !== "active") {
                return previewResult(false, "Move blocked", targetManager.full_name + " cannot receive direct reports while status is '" + targetManager.employment_status + "'.");
            }

            if (targetManager.max_direct_reports != null && targetManager.capacity_remaining <= 0) {
                return previewResult(false, "Move blocked", targetManager.full_name + " is already at direct-report capacity.");
            }

            if (rule && rule.allowed_departments.length && rule.allowed_departments.indexOf(employee.department) === -1) {
                return previewResult(false, "Move blocked", employee.department + " is not an allowed department for " + targetManager.full_name + ".");
            }

            if (rule && rule.allowed_locations.length && rule.allowed_locations.indexOf(employee.location) === -1) {
                return previewResult(false, "Move blocked", employee.location + " is not an allowed location for " + targetManager.full_name + ".");
            }

            if (rule && rule.min_child_level && compareLevels(employee.level, rule.min_child_level) < 0) {
                return previewResult(false, "Move blocked", employee.level + " is below " + targetManager.full_name + "'s allowed child-level range.");
            }

            if (rule && rule.max_child_level && compareLevels(employee.level, rule.max_child_level) > 0) {
                return previewResult(false, "Move blocked", employee.level + " is above " + targetManager.full_name + "'s allowed child-level range.");
            }

            return previewResult(true, "Valid drop target", "Drop to move " + employee.full_name + " under " + targetManager.full_name + ".");
        }

        function previewResult(valid, title, message) {
            return {
                valid: valid,
                title: title,
                message: message
            };
        }

        function isDescendant(sourceEmployeeId, targetEmployeeId) {
            var source = $scope.state.nodeMap[sourceEmployeeId];
            var stack = source ? source.children.slice() : [];

            while (stack.length) {
                var current = stack.pop();
                if (current.employee_id === targetEmployeeId) {
                    return true;
                }
                Array.prototype.push.apply(stack, current.children || []);
            }

            return false;
        }

        function compareLevels(left, right) {
            var leftKey = levelSortKey(left);
            var rightKey = levelSortKey(right);

            if (leftKey < rightKey) {
                return -1;
            }
            if (leftKey > rightKey) {
                return 1;
            }
            return 0;
        }

        function levelSortKey(level) {
            var match = String(level || "").match(/(\d+)/);
            if (match) {
                return parseInt(match[1], 10);
            }
            return String(level || "");
        }

        function emptyDiagram(message) {
            return {
                width: 0,
                height: 0,
                nodes: [],
                links: [],
                visibleCount: 0,
                totalCount: 0,
                matchedCount: 0,
                emptyMessage: message,
                visibleLookup: null,
                firstVisibleNode: null,
                byId: {}
            };
        }

        function attachViewport() {
            var nextViewport = $window.document.querySelector(".tree-viewport");

            if (viewportElement === nextViewport) {
                syncViewportSize();
                return;
            }

            if (viewportElement) {
                viewportElement.removeEventListener("wheel", onViewportWheel);
            }

            viewportElement = nextViewport;

            if (!viewportElement) {
                return;
            }

            viewportElement.addEventListener("wheel", onViewportWheel, { passive: false });
            syncViewportSize();
        }

        function onViewportWheel(event) {
            if (!$scope.state.diagram.nodes.length || $scope.state.drag.employeeId) {
                return;
            }

            event.preventDefault();

            var rect = viewportElement.getBoundingClientRect();
            var viewportX = event.clientX - rect.left;
            var viewportY = event.clientY - rect.top;
            var factor = event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP;

            zoomDiagram(factor, viewportX, viewportY);
            $scope.$applyAsync();
        }

        function onDocumentMouseMove(event) {
            if (!$scope.state.canvas.dragging) {
                return;
            }

            $scope.state.canvas.x = $scope.state.canvas.originX + (event.clientX - $scope.state.canvas.dragStartX);
            $scope.state.canvas.y = $scope.state.canvas.originY + (event.clientY - $scope.state.canvas.dragStartY);
            $scope.$applyAsync();
        }

        function stopCanvasPan() {
            $scope.state.canvas.dragging = false;
        }

        function onWindowResize() {
            if ($scope.state.mode !== "workspace") {
                return;
            }

            syncViewportSize();

            if (!$scope.state.canvas.hasInteracted) {
                fitDiagramToViewport();
                return;
            }

            $scope.$applyAsync();
        }

        function syncViewportSize() {
            if (!viewportElement) {
                return;
            }

            $scope.state.canvas.viewportWidth = viewportElement.clientWidth;
            $scope.state.canvas.viewportHeight = viewportElement.clientHeight;
        }

        function zoomAtViewportCenter(factor) {
            var viewportX = $scope.state.canvas.viewportWidth / 2;
            var viewportY = $scope.state.canvas.viewportHeight / 2;
            zoomDiagram(factor, viewportX, viewportY);
        }

        function zoomDiagram(factor, viewportX, viewportY) {
            var canvas = $scope.state.canvas;
            var nextScale = clamp(canvas.scale * factor, canvas.minScale, canvas.maxScale);

            if (nextScale === canvas.scale) {
                return;
            }

            if (viewportX == null || viewportY == null) {
                viewportX = canvas.viewportWidth / 2;
                viewportY = canvas.viewportHeight / 2;
            }

            var localX = (viewportX - canvas.x) / canvas.scale;
            var localY = (viewportY - canvas.y) / canvas.scale;

            canvas.scale = nextScale;
            canvas.x = viewportX - (localX * nextScale);
            canvas.y = viewportY - (localY * nextScale);
            canvas.hasInteracted = true;
        }

        function fitDiagramToViewport() {
            if (!$scope.state.diagram.nodes.length) {
                return;
            }

            syncViewportSize();

            var canvas = $scope.state.canvas;
            var padding = 16;
            var viewportWidth = Math.max(canvas.viewportWidth, 1);
            var viewportHeight = Math.max(canvas.viewportHeight, 1);
            var scaleX = (viewportWidth - padding) / $scope.state.diagram.width;
            var scaleY = (viewportHeight - padding) / $scope.state.diagram.height;
            var scale = clamp(Math.min(scaleX, scaleY, 1.08), canvas.minScale, canvas.maxScale);

            canvas.scale = scale;
            canvas.x = (viewportWidth - ($scope.state.diagram.width * scale)) / 2;
            canvas.y = (viewportHeight - ($scope.state.diagram.height * scale)) / 2;
            canvas.hasInteracted = false;
        }

        function focusNode(node) {
            if (!node || !$scope.state.diagram.byId[node.employee_id]) {
                return;
            }

            syncViewportSize();

            var canvas = $scope.state.canvas;
            var renderNode = $scope.state.diagram.byId[node.employee_id];
            var targetScale = clamp(Math.max(canvas.scale, 0.95), canvas.minScale, canvas.maxScale);

            canvas.scale = targetScale;
            canvas.x = (canvas.viewportWidth / 2) - (renderNode.centerX * targetScale);
            canvas.y = (canvas.viewportHeight / 2) - (renderNode.centerY * targetScale);
            canvas.hasInteracted = true;
        }

        function getDepartmentAccent(department) {
            var normalized = (department || "").toLowerCase();

            if (normalized === "executive") {
                return "#f2665f";
            }
            if (normalized === "engineering" || normalized === "data") {
                return "#654ea3";
            }
            if (normalized === "sales") {
                return "#fdb515";
            }
            if (normalized === "people") {
                return "#516dc4";
            }
            return "#3d3a56";
        }

        function isInteractiveTarget(target) {
            return !!closestElement(target, ".org-node, .canvas-control, input, select, button, label, .org-node__drag-handle");
        }

        function closestElement(element, selector) {
            while (element) {
                if (element.matches && element.matches(selector)) {
                    return element;
                }
                element = element.parentElement;
            }
            return null;
        }

        function clamp(value, minValue, maxValue) {
            return Math.max(minValue, Math.min(maxValue, value));
        }

        function getCurrentChangeLog() {
            return (($scope.state.treePayload && $scope.state.treePayload.change_log) || []);
        }

        function setSavedBaseline(payload, snapshotInfo) {
            $scope.state.lastSavedPayload = angular.copy(payload);
            $scope.state.lastSavedSnapshot = snapshotInfo || null;
            if (snapshotInfo && snapshotInfo.path) {
                $scope.state.selectedSnapshotPath = snapshotInfo.path;
            }
        }

        function loadSnapshots(preferredSnapshotPath) {
            if (!$scope.state.mode || $scope.state.mode !== "workspace" || !$scope.canUseSnapshotStorage()) {
                $scope.state.snapshotOptions = [];
                if (!$scope.canUseSnapshotStorage()) {
                    $scope.state.selectedSnapshotPath = "";
                }
                return;
            }

            $scope.state.snapshotsLoading = true;

            $http.post(getWebAppBackendUrl("list-snapshots"), angular.extend({}, buildRequestPayload(), {
                snapshot_folder: $scope.state.form.snapshotFolder
            }))
                .then(function(response) {
                    var snapshots = (response.data && response.data.snapshots) || [];
                    $scope.state.snapshotsLoading = false;
                    $scope.state.snapshotOptions = snapshots;

                    if (preferredSnapshotPath) {
                        $scope.state.selectedSnapshotPath = preferredSnapshotPath;
                    } else if ($scope.state.selectedSnapshotPath && snapshots.some(function(snapshot) {
                        return snapshot.path === $scope.state.selectedSnapshotPath;
                    })) {
                        return;
                    } else {
                        $scope.state.selectedSnapshotPath = snapshots.length ? snapshots[0].path : "";
                    }
                }, function() {
                    $scope.state.snapshotsLoading = false;
                    $scope.state.snapshotOptions = [];
                    $scope.state.selectedSnapshotPath = "";
                });
        }

        function downloadFile(filePayload) {
            if (!filePayload || !filePayload.content) {
                return;
            }

            var blob = new Blob([filePayload.content], {
                type: filePayload.content_type || "text/plain"
            });
            var objectUrl = $window.URL.createObjectURL(blob);
            var link = $window.document.createElement("a");

            link.href = objectUrl;
            link.download = filePayload.filename || "download.txt";
            $window.document.body.appendChild(link);
            link.click();
            $window.document.body.removeChild(link);
            $window.URL.revokeObjectURL(objectUrl);
        }

        function defaultFilters() {
            return {
                search: "",
                department: "",
                location: "",
                status: "",
                onlyWarnings: false
            };
        }

        function defaultDragState() {
            return {
                employeeId: null,
                hoverTargetId: null,
                preview: null
            };
        }

        function clearDragState() {
            $scope.state.drag = defaultDragState();
        }

        function handleBackendError(error, fallbackMessage) {
            var payload = error && error.data ? error.data : {};
            $scope.state.backendError = {
                title: fallbackMessage,
                message: payload.message || payload.error || fallbackMessage,
                issues: payload.issues || []
            };
        }

        function handleMoveError(error) {
            var payload = error && error.data ? error.data : {};
            $scope.state.moveFeedback = {
                tone: "error",
                title: "Move rejected",
                message: payload.message || "The move was rejected by backend validation.",
                issues: (payload.issues || []).map(function(issue) {
                    return issue.message || String(issue);
                })
            };
        }
    });

    app.directive("orgDragHandle", function() {
        return {
            restrict: "A",
            link: function(scope, element, attrs) {
                element.attr("draggable", "true");

                element.on("mousedown", function(event) {
                    event.stopPropagation();
                });

                element.on("click", function(event) {
                    event.preventDefault();
                    event.stopPropagation();
                });

                element.on("dragstart", function(event) {
                    var nativeEvent = event.originalEvent || event;
                    var employeeId = scope.$eval(attrs.employeeId);

                    if (nativeEvent.dataTransfer) {
                        nativeEvent.dataTransfer.effectAllowed = "move";
                        try {
                            nativeEvent.dataTransfer.setData("text/plain", String(employeeId));
                        } catch (ignoreError) {
                        }
                    }

                    scope.$applyAsync(function() {
                        scope.startNodeDrag(employeeId);
                    });
                });

                element.on("dragend", function() {
                    scope.$applyAsync(function() {
                        scope.endNodeDrag();
                    });
                });
            }
        };
    });

    app.directive("orgDropTarget", function() {
        return {
            restrict: "A",
            link: function(scope, element, attrs) {
                function getEmployeeId() {
                    return scope.$eval(attrs.employeeId);
                }

                function updatePreview(nativeEvent) {
                    var valid = scope.updateDropTarget(getEmployeeId());
                    if (nativeEvent.dataTransfer) {
                        nativeEvent.dataTransfer.dropEffect = valid ? "move" : "none";
                    }
                    return valid;
                }

                element.on("dragenter", function(event) {
                    var nativeEvent = event.originalEvent || event;
                    nativeEvent.preventDefault();
                    scope.$applyAsync(function() {
                        updatePreview(nativeEvent);
                    });
                });

                element.on("dragover", function(event) {
                    var nativeEvent = event.originalEvent || event;
                    nativeEvent.preventDefault();
                    scope.$applyAsync(function() {
                        updatePreview(nativeEvent);
                    });
                });

                element.on("drop", function(event) {
                    var nativeEvent = event.originalEvent || event;
                    nativeEvent.preventDefault();
                    scope.$applyAsync(function() {
                        scope.completeDrop(getEmployeeId());
                    });
                });
            }
        };
    });
})();
