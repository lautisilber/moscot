from typing import Tuple

import pytest

import numpy as np
import pandas as pd

from anndata import AnnData

from moscot.problems.time import TemporalProblem
from tests._utils import MockSolverOutput


class TestTemporalMixin:
    @pytest.mark.fast()
    @pytest.mark.parametrize("forward", [True, False])
    def test_cell_transition_full_pipeline(self, gt_temporal_adata: AnnData, forward: bool):
        config = gt_temporal_adata.uns
        key = config["key"]
        key_1 = config["key_1"]
        key_2 = config["key_2"]
        key_3 = config["key_3"]
        cell_types = set(gt_temporal_adata.obs["cell_type"].cat.categories)
        problem = TemporalProblem(gt_temporal_adata)
        problem = problem.prepare(key)
        assert set(problem.problems.keys()) == {(key_1, key_2), (key_2, key_3)}
        problem[key_1, key_2]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_105"])
        problem[key_2, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_105_11"])

        cell_types_present_key_1 = (
            gt_temporal_adata[gt_temporal_adata.obs[key] == key_1].obs["cell_type"].cat.categories
        )
        cell_types_present_key_2 = (
            gt_temporal_adata[gt_temporal_adata.obs[key] == key_2].obs["cell_type"].cat.categories
        )

        result = problem.cell_transition(
            key_1,
            key_2,
            "cell_type",
            "cell_type",
            forward=forward,
        )
        assert isinstance(result, pd.DataFrame)
        expected_shape = (len(cell_types_present_key_1), len(cell_types_present_key_2))
        assert result.shape == expected_shape
        assert set(result.index) == set(cell_types_present_key_1) if forward else set(cell_types)
        assert set(result.columns) == set(cell_types_present_key_2) if not forward else set(cell_types)
        marginal = result.sum(axis=forward == 1).values
        present_cell_type_marginal = marginal[marginal > 0]
        np.testing.assert_allclose(present_cell_type_marginal, 1.0)

    @pytest.mark.fast()
    @pytest.mark.parametrize(
        "forward",
        [
            True,
        ],
    )  # False])
    @pytest.mark.parametrize("mapping_mode", ["max"])  # , "sum"])
    @pytest.mark.parametrize("problem_kind", ["temporal"])
    def test_annotation_mapping(self, adata_anno: AnnData, forward: bool, mapping_mode, gt_tm_annotation):
        problem = TemporalProblem(adata_anno)
        problem_keys = (0, 1)
        problem = problem.prepare(time_key="day", joint_attr="X_pca")
        assert set(problem.problems.keys()) == {problem_keys}
        problem[problem_keys]._solution = MockSolverOutput(gt_tm_annotation)
        result = problem.annotation_mapping(
            mapping_mode=mapping_mode, annotation_label="celltype", forward=forward, source=0, target=1
        )
        expected_result = adata_anno.uns["expected_max"] if mapping_mode == "max" else adata_anno.uns["expected_sum"]
        assert (result["celltype"] == expected_result).all()

    @pytest.mark.fast()
    @pytest.mark.parametrize("forward", [True, False])
    def test_cell_transition_different_groups(self, gt_temporal_adata: AnnData, forward: bool):
        config = gt_temporal_adata.uns
        key = config["key"]
        key_1 = config["key_1"]
        key_2 = config["key_2"]
        key_3 = config["key_3"]

        gt_temporal_adata.obs["batch"] = gt_temporal_adata.obs["batch"].astype("category")
        batches = set(gt_temporal_adata.obs["batch"].cat.categories)
        problem = TemporalProblem(gt_temporal_adata)
        problem = problem.prepare(key)
        assert set(problem.problems.keys()) == {(key_1, key_2), (key_2, key_3)}
        problem[key_1, key_2]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_105"])
        problem[key_2, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_105_11"])

        result = problem.cell_transition(
            key_1,
            key_2,
            "cell_type",
            "batch",
            forward=forward,
        )
        assert isinstance(result, pd.DataFrame)
        cell_types = set(gt_temporal_adata[gt_temporal_adata.obs[key] == key_1].obs["cell_type"].cat.categories)
        batches = set(gt_temporal_adata[gt_temporal_adata.obs[key] == key_2].obs["batch"].cat.categories)
        assert set(result.index) == cell_types
        assert set(result.columns) == batches

    @pytest.mark.fast()
    @pytest.mark.parametrize("forward", [True, False])
    def test_cell_transition_subset_pipeline(self, gt_temporal_adata: AnnData, forward: bool):
        config = gt_temporal_adata.uns
        key = config["key"]
        key_1 = config["key_1"]
        key_2 = config["key_2"]
        key_3 = config["key_3"]
        problem = TemporalProblem(gt_temporal_adata)
        problem = problem.prepare(key)
        assert set(problem.problems.keys()) == {(key_1, key_2), (key_2, key_3)}
        problem[key_1, key_2]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_105"])
        problem[key_2, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_105_11"])

        early_annotation = ["Stromal", "unknown"]
        late_annotation = ["Stromal", "Epithelial"]
        result = problem.cell_transition(
            key_1,
            key_2,
            {"cell_type": early_annotation},
            {"cell_type": late_annotation},
            forward=forward,
        )
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (len(early_annotation), len(late_annotation))
        assert set(result.index) == set(early_annotation)
        assert set(result.columns) == set(late_annotation)

        marginal = result.sum(axis=forward == 1).values
        present_cell_type_marginal = marginal[marginal > 0]
        np.testing.assert_allclose(present_cell_type_marginal, np.ones(len(present_cell_type_marginal)))

    @pytest.mark.parametrize("forward", [True, False])
    def test_cell_transition_regression(self, gt_temporal_adata: AnnData, forward: bool):
        config = gt_temporal_adata.uns
        key = config["key"]
        key_1 = config["key_1"]
        key_2 = config["key_2"]
        key_3 = config["key_3"]
        problem = TemporalProblem(gt_temporal_adata)
        problem = problem.prepare(key)
        assert set(problem.problems.keys()) == {(key_1, key_2), (key_2, key_3)}
        problem[key_1, key_2]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_105"])
        problem[key_2, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_105_11"])
        result = problem.cell_transition(
            10,
            10.5,
            source_groups="cell_type",
            target_groups="cell_type",
            forward=forward,
        )
        cell_types_present_key_1 = (
            gt_temporal_adata[gt_temporal_adata.obs[key] == key_1].obs["cell_type"].cat.categories
        )
        cell_types_present_key_2 = (
            gt_temporal_adata[gt_temporal_adata.obs[key] == key_2].obs["cell_type"].cat.categories
        )
        expected_shape = (
            (len(cell_types_present_key_1), len(cell_types_present_key_2))
            if forward
            else (len(cell_types_present_key_1), len(cell_types_present_key_2))
        )
        assert result.shape == expected_shape
        marginal = result.sum(axis=forward == 1).values
        present_cell_type_marginal = marginal[marginal > 0]
        np.testing.assert_allclose(present_cell_type_marginal, 1.0, rtol=1e-6, atol=1e-6)

        direction = "forward" if forward else "backward"
        gt = gt_temporal_adata.uns[f"cell_transition_10_105_{direction}"]
        gt = gt.sort_index()
        result = result.sort_index()
        result = result[gt.columns]
        np.testing.assert_allclose(result.values, gt.values, rtol=1e-6, atol=1e-6)

    def test_compute_time_point_distances_pipeline(self, adata_time: AnnData):
        problem = TemporalProblem(adata_time).prepare("time")
        distance_source_intermediate, distance_intermediate_target = problem.compute_time_point_distances(
            source=0,
            intermediate=1,
            target=2,
            posterior_marginals=False,
            epsilon=10,
        )
        assert distance_source_intermediate > 0
        assert distance_source_intermediate < 100
        assert distance_intermediate_target > 0

    def test_batch_distances_pipeline(self, adata_time: AnnData):
        problem = TemporalProblem(adata_time)
        problem.prepare("time")

        batch_distance = problem.compute_batch_distances(time=1, batch_key="batch", epsilon=10)
        assert batch_distance > 0

    @pytest.mark.parametrize("account_for_unbalancedness", [True, False])
    def test_compute_interpolated_distance_pipeline(self, gt_temporal_adata: AnnData, account_for_unbalancedness: bool):
        config = gt_temporal_adata.uns
        key = config["key"]
        key_1 = config["key_1"]
        key_2 = config["key_2"]
        key_3 = config["key_3"]
        problem = TemporalProblem(gt_temporal_adata)
        problem = problem.prepare(
            key,
            subset=[(key_1, key_2), (key_2, key_3), (key_1, key_3)],
            policy="explicit",
            xy_callback_kwargs={"n_comps": 50},
        )
        assert set(problem.problems.keys()) == {(key_1, key_2), (key_2, key_3), (key_1, key_3)}
        problem[key_1, key_2]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_105"])
        problem[key_2, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_105_11"])
        problem[key_1, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_11"])

        interpolation_result = problem.compute_interpolated_distance(
            key_1,
            key_2,
            key_3,
            account_for_unbalancedness=account_for_unbalancedness,
            posterior_marginals=False,
            seed=config["seed"],
            epsilon=10,
        )
        assert isinstance(interpolation_result, float)
        assert interpolation_result > 0

    def test_compute_interpolated_distance_regression(self, gt_temporal_adata: AnnData):
        config = gt_temporal_adata.uns
        key = config["key"]
        key_1 = config["key_1"]
        key_2 = config["key_2"]
        key_3 = config["key_3"]
        problem = TemporalProblem(gt_temporal_adata)
        problem = problem.prepare(
            key,
            subset=[(key_1, key_2), (key_2, key_3), (key_1, key_3)],
            policy="explicit",
            scale_cost="mean",
            xy_callback_kwargs={"n_comps": 50},
        )
        assert set(problem.problems.keys()) == {(key_1, key_2), (key_2, key_3), (key_1, key_3)}
        problem[key_1, key_2]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_105"])
        problem[key_2, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_105_11"])
        problem[key_1, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_11"])

        interpolation_result = problem.compute_interpolated_distance(
            key_1, key_2, key_3, posterior_marginals=False, seed=config["seed"], epsilon=10
        )
        assert isinstance(interpolation_result, float)
        assert interpolation_result > 0
        np.testing.assert_allclose(
            interpolation_result, gt_temporal_adata.uns["interpolated_distance_10_105_11"], rtol=1e-6, atol=1e-6
        )

    def test_compute_time_point_distances_regression(self, gt_temporal_adata: AnnData):
        config = gt_temporal_adata.uns
        key = config["key"]
        key_1 = config["key_1"]
        key_2 = config["key_2"]
        key_3 = config["key_3"]
        problem = TemporalProblem(gt_temporal_adata)
        problem = problem.prepare(
            key,
            subset=[(key_1, key_2), (key_2, key_3), (key_1, key_3)],
            policy="explicit",
            scale_cost="mean",
            xy_callback_kwargs={"n_comps": 50},
        )
        assert set(problem.problems.keys()) == {(key_1, key_2), (key_2, key_3), (key_1, key_3)}
        problem[key_1, key_2]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_105"])
        problem[key_2, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_105_11"])
        problem[key_1, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_11"])

        result = problem.compute_time_point_distances(key_1, key_2, key_3, posterior_marginals=False, epsilon=10)
        assert isinstance(result, tuple)
        assert result[0] > 0
        assert result[1] > 0
        np.testing.assert_allclose(
            result[0], gt_temporal_adata.uns["time_point_distances_10_105_11"][0], rtol=1e-6, atol=1e-6
        )
        np.testing.assert_allclose(
            result[1], gt_temporal_adata.uns["time_point_distances_10_105_11"][1], rtol=1e-6, atol=1e-6
        )

    def test_compute_batch_distances_regression(self, gt_temporal_adata: AnnData):
        config = gt_temporal_adata.uns
        key = config["key"]
        key_1 = config["key_1"]
        key_2 = config["key_2"]
        key_3 = config["key_3"]
        problem = TemporalProblem(gt_temporal_adata)
        problem = problem.prepare(
            key,
            subset=[(key_1, key_2), (key_2, key_3), (key_1, key_3)],
            policy="explicit",
            scale_cost="mean",
            xy_callback_kwargs={"n_comps": 50},
        )
        assert set(problem.problems.keys()) == {(key_1, key_2), (key_2, key_3), (key_1, key_3)}
        problem[key_1, key_2]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_105"])
        problem[key_2, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_105_11"])
        problem[key_1, key_3]._solution = MockSolverOutput(gt_temporal_adata.uns["tmap_10_11"])

        result = problem.compute_batch_distances(key_1, "batch", epsilon=10)
        assert isinstance(result, float)
        np.testing.assert_allclose(result, gt_temporal_adata.uns["batch_distances_10"], rtol=1e-5)

    def test_compute_random_distance_regression(self, gt_temporal_adata: AnnData):
        config = gt_temporal_adata.uns
        key = config["key"]
        key_1 = config["key_1"]
        key_2 = config["key_2"]
        key_3 = config["key_3"]
        problem = TemporalProblem(gt_temporal_adata)
        problem = problem.prepare(
            key,
            subset=[(key_1, key_2), (key_2, key_3), (key_1, key_3)],
            policy="explicit",
            scale_cost="mean",
            xy_callback_kwargs={"n_comps": 50},
        )
        assert set(problem.problems.keys()) == {(key_1, key_2), (key_2, key_3), (key_1, key_3)}

        result = problem.compute_random_distance(
            key_1, key_2, key_3, posterior_marginals=False, seed=config["seed"], epsilon=10
        )
        assert isinstance(result, float)
        np.testing.assert_allclose(result, gt_temporal_adata.uns["random_distance_10_105_11"], rtol=1e-6, atol=1e-6)

    # TODO(MUCDK): split into 2 tests
    @pytest.mark.fast()
    @pytest.mark.parametrize("only_start", [True, False])
    def test_get_data_pipeline(self, adata_time: AnnData, only_start: bool):
        problem = TemporalProblem(adata_time)
        problem.prepare("time")

        # TODO(MUCDK): use namedtuple
        result = (
            problem._get_data(0, only_start=only_start, posterior_marginals=False)
            if only_start
            else problem._get_data(0, 1, 2, posterior_marginals=False)
        )

        assert isinstance(result, tuple)
        assert len(result) == 2 if only_start else len(result) == 5
        if only_start:
            assert isinstance(result[0], np.ndarray)
            assert isinstance(result[1], AnnData)
        else:
            assert isinstance(result[0], np.ndarray)
            # assert isinstance(result[1], np.ndarray)  # FIXME: None growth-rates
            assert isinstance(result[2], np.ndarray)
            assert isinstance(result[3], AnnData)
            assert isinstance(result[4], np.ndarray)

    @pytest.mark.parametrize("time_points", [(0, 1, 2), (0, 2, 1), ()])
    def test_get_interp_param_pipeline(self, adata_time: AnnData, time_points: Tuple[float]):
        start, intermediate, end = time_points if len(time_points) else (42, 43, 44)
        interpolation_parameter = None if len(time_points) == 3 else 0.5
        problem = TemporalProblem(adata_time)
        problem.prepare("time")
        problem.solve(max_iterations=2)

        if intermediate <= start or end <= intermediate:
            with np.testing.assert_raises(ValueError):
                problem._get_interp_param(start, intermediate, end, interpolation_parameter)
        else:
            inter_param = problem._get_interp_param(start, intermediate, end, interpolation_parameter)
            assert inter_param == 0.5

    @pytest.mark.fast()
    def test_cell_transition_regression_notparam(
        self,
        adata_time_with_tmap: AnnData,
    ):  # TODO(MUCDK): please check.
        problem = TemporalProblem(adata_time_with_tmap).prepare("time")
        problem[0, 1]._solution = MockSolverOutput(adata_time_with_tmap.uns["transport_matrix"])

        result = problem.cell_transition(
            0,
            1,
            source_groups="cell_type",
            target_groups="cell_type",
            forward=True,
        )
        res = result.sort_index().sort_index(axis=1)
        df_expected = adata_time_with_tmap.uns["cell_transition_gt"].sort_index().sort_index(axis=1)
        # TODO(MUCDK): use pandas.testing
        np.testing.assert_allclose(res.values, df_expected.values, rtol=1e-6, atol=1e-6)

    @pytest.mark.fast()
    @pytest.mark.parametrize("temporal_key", ["celltype", "time", "missing"])
    def test_temporal_key_numeric(self, adata_time: AnnData, temporal_key: str):
        problem = TemporalProblem(adata_time)
        if temporal_key == "missing":
            with pytest.raises(KeyError, match=r"Unable to find temporal key"):
                _ = problem.prepare(temporal_key)
        elif temporal_key == "celltype":
            with pytest.raises(TypeError, match=rf"Expected `adata.obs\[{temporal_key!r}\]`.*"):
                _ = problem.prepare(temporal_key)
        elif temporal_key == "time":
            _ = problem.prepare(temporal_key)
        else:
            raise NotImplementedError(temporal_key)
