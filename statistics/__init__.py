from pathlib import Path
import numpy as np
import pandas as pd
import math
from data import BreastCancer, SpliceJunction, CensusIncome
from results import PATH as RESULT_PATH

PATH = Path(__file__).parents[0]


def apply_noise(data: pd.DataFrame, mu: float, sigma: float, dataset_name: str, seed: int) -> pd.DataFrame:
    """
    Apply noise to the data.
    :param data: the dataset
    :param mu: center of the distribution
    :param sigma: standard deviation of the distribution
    :param dataset_name:
    :param seed: the seed for the random number generator
    :return:
    """
    if dataset_name == BreastCancer.name:
        return _apply_noise_to_breast_cancer(data, mu, sigma, seed)
    elif dataset_name == SpliceJunction.name:
        return _apply_noise_to_splice_junction(data, mu, sigma, seed)
    elif dataset_name == CensusIncome.name:
        return _apply_noise_to_census_income(data, mu, sigma, seed)
    else:
        raise ValueError('The dataset name is not valid.')


def _add_noise_to_ordinal_feature(feature: str, data: pd.DataFrame, mu: float, sigma: float):
    """
    Add noise to an ordinal feature.
    :param feature: the feature to add noise to
    :param data: the dataset
    :param mu: center of the distribution
    :param sigma: standard deviation of the distribution
    :return:
    """
    maximum_value = data[feature].max()
    minimum_value = data[feature].min()
    data[feature] = data[feature].apply(lambda j: round(j + np.random.normal(mu, sigma)))
    data[feature] = data[feature].apply(lambda j: maximum_value if j > maximum_value else j)
    data[feature] = data[feature].apply(lambda j: minimum_value if j < minimum_value else j)


def _apply_noise_to_breast_cancer(data: pd.DataFrame, mu: float, sigma: float, seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    data_copy = data.copy()
    for feature in data.columns:
        _add_noise_to_ordinal_feature(feature, data_copy, mu, sigma)
    return data_copy


def _apply_noise_to_splice_junction(data: pd.DataFrame, mu: float, sigma: float, seed: int) -> pd.DataFrame:
    data_copy = data.copy()
    # First, a random order is generated for the 4 basis (a, c, g, t).
    # This order is always the same for a given seed.
    # Then, features are grouped into 60 macro-features, each macro-feature has 4 features.
    # For each feature in a macro-feature, if the feature is 1, then the value of the feature is changed according to
    # the noise and the random order. Otherwise, the value is not changed.
    np.random.seed(0)
    basis_order = np.random.choice(['a', 'c', 'g', 't'], 4, replace=False)
    np.random.seed(seed)
    basis_mapping = {k: v for v, k in enumerate(basis_order)}
    original_mapping = {0: 'a', 1: 'c', 2: 'g', 3: 't'}
    for i in range(0, 60):
        new_values_i = []
        for j in range(0, 4):
            feature = data.columns[i * 4 + j]
            new_values = data_copy[feature].apply(
                lambda k: round(basis_mapping[original_mapping[j]] + np.random.normal(mu, sigma)) if k == 1 else np.nan)
            new_values = new_values.apply(lambda k: 3 if k > 3 else k)
            new_values = new_values.apply(lambda k: 0 if k < 0 else k)
            new_values_i.append(new_values)
        new_values_i = pd.DataFrame(new_values_i).T
        for j in range(0, 4):
            feature = data.columns[i * 4 + j]
            data_copy[feature] = new_values_i.apply(lambda k: 1 if basis_mapping[original_mapping[j]] in list(k) else 0,
                                                    axis=1)
    return data_copy


def _apply_noise_to_census_income(data: pd.DataFrame, mu: float, sigma: float, seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    data_copy = data.copy()
    for integer_feature in CensusIncome.integer_features:
        data_copy[integer_feature] = data_copy[integer_feature].apply(lambda j: round(j + np.random.normal(mu, sigma)))
        if integer_feature == "Age":
            data_copy[integer_feature] = data_copy[integer_feature].apply(lambda j: 0 if j < 0 else j)
        elif integer_feature == "HoursPerWeek":
            data_copy[integer_feature] = data_copy[integer_feature].apply(lambda j: 0 if j < 0 else j)
            data_copy[integer_feature] = data_copy[integer_feature].apply(lambda j: 99 if j > 99 else j)
    for binary_feature in CensusIncome.binary_features:
        data_copy[binary_feature] = data_copy[binary_feature].apply(lambda j: round(j + np.random.normal(mu, sigma)))
        data_copy[binary_feature] = data_copy[binary_feature].apply(lambda j: 1 if j > 1 else j)
        data_copy[binary_feature] = data_copy[binary_feature].apply(lambda j: 0 if j < 0 else j)
    for ordinal_feature in CensusIncome.ordinal_features:
        _add_noise_to_ordinal_feature(ordinal_feature, data_copy, mu, sigma)
    for nominal_feature in CensusIncome.nominal_features:
        values = [f for f in data_copy.columns if f.startswith(nominal_feature)]
        original_mapping = {k: v for k, v in enumerate(values)}
        np.random.seed(0)
        new_order = np.random.choice(values, len(values), replace=False)
        new_mapping = {k: v for v, k in enumerate(new_order)}
        inverse_new_mapping = {v: k for k, v in new_mapping.items()}
        indices = data_copy[values].apply(lambda j: np.argmax(j), axis=1)
        np.random.seed(seed)
        indices = indices.apply(lambda j: round(new_mapping[original_mapping[j]] + np.random.normal(mu, sigma)))
        indices = indices.apply(lambda j: len(values) - 1 if j > len(values) - 1 else j)
        indices = indices.apply(lambda j: 0 if j < 0 else j)
        for value in values:
            data_copy[value] = indices.apply(lambda j: 1 if inverse_new_mapping[j] == value else 0)
    return data_copy


def flip_labels(data: pd.DataFrame, label_flip_p: float, dataset_name: str, seed: int) -> pd.DataFrame:
    """
    Apply label flipping to the data.
    :param data: the dataset
    :param label_flip_p: probability of flipping a label
    :param dataset_name:
    :param seed: the seed for the random number generator
    :return:
    """
    if dataset_name == BreastCancer.name:
        label_name = 'diagnosis'
    elif dataset_name == SpliceJunction.name:
        label_name = 'class'
    elif dataset_name == CensusIncome.name:
        label_name = 'income'
    else:
        raise ValueError('The dataset name is not valid.')
    # Seed the flipping process
    np.random.seed(seed)
    data_copy = data.copy()
    possible_labels = list(set(data_copy[label_name].tolist()))

    def random_flip(label, flipping_prob):
        if np.random.choice([1, 0], p=[flipping_prob, 1 - flipping_prob]) == 1:
            return np.random.choice([lab for lab in possible_labels if lab != label])
        else:
            return label

    data_copy[label_name] = data_copy[label_name].apply(lambda j: random_flip(j, label_flip_p))
    return data_copy


def reverse_one_hot(data: pd.DataFrame, one_hot_features: list) -> pd.DataFrame:
    reformatted_data = data.copy()
    for feature in one_hot_features:
        columns = [col for col in data.columns if col.startswith(feature)]
        reformatted_data.drop(columns, axis=1, inplace=True)
        skimmed_data = data[columns]
        reversed_data = skimmed_data.apply(lambda x: np.argmax(x), axis=1)
        reformatted_data[feature] = reversed_data
    return reformatted_data


def reverse_multi_hot(data: pd.DataFrame) -> pd.DataFrame:
    reformatted_data = pd.DataFrame()
    for i in range(60):
        values = []
        for j in range(4):
            values.append(data.iloc[:, j + i * 4])
        values = pd.DataFrame(values).T
        values = values.apply(lambda x: sum(x * [1, 3, 5, 10]), axis=1)
        reformatted_data[str(i)] = values
    reformatted_data['class'] = data['class']
    return reformatted_data


def compute_divergence(original_data: pd.DataFrame, perturbed_data: pd.DataFrame) -> float:
    if 'class' in original_data:
        dataset_name = 'splice-junction'
        original_data = reverse_multi_hot(original_data)
        perturbed_data = reverse_multi_hot(perturbed_data)
        label_col = 'class'
    elif 'income' in original_data:
        dataset_name = 'census-income'
        one_hot_features = CensusIncome.one_hot_features
        original_data = reverse_one_hot(original_data, one_hot_features)
        perturbed_data = reverse_one_hot(perturbed_data, one_hot_features)
        label_col = 'income'
    elif 'diagnosis' in original_data:
        dataset_name = 'breast-cancer'
        label_col = 'diagnosis'
    else:
        raise ValueError('The dataset name is not valid.')
    labels_original = original_data[label_col]
    try:
        labels_perturbed = perturbed_data[label_col]
    except KeyError:
        raise ValueError('The two datasets appear to have different labels!')
    assert set(labels_original) == set(labels_perturbed)
    labels = set(labels_original)
    divergence_score = 0.
    for label in labels:
        data1 = original_data[original_data[label_col] == label]
        data2 = perturbed_data[perturbed_data[label_col] == label]
        data1 = data1.drop(columns=[label_col])
        data2 = data2.drop(columns=[label_col])
        label_divergence = _compute_kl_div(data1=data1,
                                           data2=data2)
        divergence_score = divergence_score + label_divergence * len(data1.index)
    divergence_score = divergence_score / float(len(original_data.index))
    print('divergence_score: {}'.format(divergence_score))
    return divergence_score


def _compute_kl_div(data1: pd.DataFrame, data2: pd.DataFrame) -> float:
    for feat in data2.columns:
        if len(set(data2[feat].unique())) == 1:
            data1.drop(feat, axis=1, inplace=True)
            data2.drop(feat, axis=1, inplace=True)

    # First convert to np array
    data1_array = np.array(data1)
    data2_array = np.array(data2)
    # print(data2_array.shape)

    # Then compute their means
    mu_data1 = np.mean(data1_array, axis=0)
    mu_data2 = np.mean(data2_array, axis=0)

    # Compute their covariance
    cov_data1 = np.cov(data1_array, rowvar=False)
    cov_data2 = np.cov(data2_array, rowvar=False)

    try:
        cov_q_inv = np.linalg.inv(cov_data2)
    except np.linalg.LinAlgError:
        cov_q_inv = np.linalg.pinv(cov_data2)

    det2 = np.linalg.det(cov_data2)
    det1 = np.linalg.det(cov_data1)

    kl = 0.5 * (np.log(det2 / det1) - mu_data1.shape[0] + np.trace(cov_q_inv @ cov_data1) +
                (mu_data1 - mu_data2).T @ cov_q_inv @ (mu_data1 - mu_data2))

    if math.isnan(kl) or abs(kl) > 1e7:
        kl = 10000.

    if kl < 0:
        kl = 0

    print('kl value: {}'.format(kl))

    return kl


def compute_robustness(perturbation: str, dataset: BreastCancer or SpliceJunction or CensusIncome, metric: str) -> dict:
    models = ['uneducated', 'kins', 'kill', 'kbann']
    robustness_dict = {}
    n = 10 if perturbation in ['noise', 'label_flip'] else 20

    def f(x):
        return np.asarray([abs(y) if y < 0 else 1E-5 for y in x])

    for model in models:
        pi1 = pd.read_csv(RESULT_PATH / 'drop' / dataset.name / model / '1.csv')
        pi1 = np.mean(pi1[metric])
        divergences = []
        pi2 = []
        for i in range(n) if perturbation == 'noise' else range(1, n):
            divergences.append(
                np.mean(pd.read_csv(RESULT_PATH / perturbation / dataset.name / 'divergences' / f'{i + 1}.csv'))[0])
            pi2.append(np.mean(pd.read_csv(RESULT_PATH / perturbation / dataset.name / model / f'{i + 1}.csv')[metric]))
        robustness_dict[model + ' absolute'] = (sum(np.asarray(divergences) / (pi1 / pi2)) / n)
    for model in models:
        robustness_dict[model + ' relative'] = robustness_dict[model + ' absolute'] / robustness_dict[
            'uneducated absolute']

    return robustness_dict
